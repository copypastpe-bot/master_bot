"""Client bot - for clients to view bonuses, history, and make requests."""

import logging
from datetime import date, datetime

from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, TelegramObject, MenuButtonWebApp, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest
from typing import Callable, Dict, Any, Awaitable

from src.config import CLIENT_BOT_TOKEN, MASTER_BOT_TOKEN, LOG_LEVEL, MINIAPP_URL
from src.states import (
    ClientRegistration, ClientDeletion, OrderRequestFSM, QuestionFSM, MediaFSM,
    ClientRescheduleOrder, ClientCancelOrder,
)
from src.keyboards import (
    home_client_kb, client_bonuses_kb, client_bot_history_kb,
    client_promos_kb, client_master_info_kb, client_notifications_kb,
    client_settings_kb, client_notifications_back_kb,
    skip_kb, share_contact_kb, stub_kb, home_reply_kb,
    order_request_services_kb, order_request_comment_kb, order_request_confirm_kb,
    question_cancel_kb, media_cancel_kb, media_comment_kb, client_home_kb,
    client_reschedule_calendar_kb, client_reschedule_hour_kb,
    client_reschedule_minutes_kb, client_reschedule_confirm_kb,
    client_cancel_reason_kb, client_cancel_confirm_kb,
    consent_kb, delete_confirm_kb, back_kb,
)
from src.database import (
    init_db,
    get_master_by_invite_token,
    get_master_by_id,
    get_client_by_tg_id,
    get_client_by_phone,
    create_client,
    update_client,
    link_client_to_master,
    get_master_client,
    get_master_client_by_client_tg_id,
    get_all_client_masters_by_tg_id,
    link_existing_client_to_master,
    save_client_home_message_id,
    toggle_client_notification,
    get_client_orders,
    get_client_bonus_log,
    get_active_campaigns,
    get_order_for_confirmation,
    get_master_services_for_client,
    save_inbound_request,
    mark_order_confirmed_by_client,
    update_order_schedule,
    update_order_status,
    reset_order_for_reconfirmation,
    accrue_welcome_bonus,
    anonymize_client,
    update_client_consent,
)
from src.utils import (
    format_phone, parse_date, normalize_phone,
    render_bonus_message, DEFAULT_WELCOME_MESSAGE,
    get_currency_symbol,
)

# Master bot instance for sending notifications
master_bot: Bot = None

# Active master selection for multi-master clients (tg_id → master_id)
_active_masters: dict[int, int] = {}

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize router
router = Router()

MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]


# =============================================================================
# Home Screen
# =============================================================================

async def build_home_text(client, master, master_client) -> str:
    """Build home screen text."""
    curr = get_currency_symbol(master.currency)
    return (
        f"👋 Привет, {client.name}!\n\n"
        f"💰 Ваши бонусы: {master_client.bonus_balance} {curr}\n"
        f"Мастер: {master.name}\n"
        f"━━━━━━━━━━━━━━━"
    )


async def show_home(bot: Bot, client, master, master_client, chat_id: int, force_new: bool = False) -> int:
    """Show or update home screen. Returns message_id.

    Args:
        force_new: If True, always send new message (delete old if exists)
    """
    text = await build_home_text(client, master, master_client)
    all_masters = await get_all_client_masters_by_tg_id(client.tg_id)
    keyboard = home_client_kb(multi_master=len(all_masters) > 1)

    # Delete old message if force_new
    if force_new and master_client.home_message_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=master_client.home_message_id)
        except TelegramBadRequest:
            pass
        # Send new message
        msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
        await save_client_home_message_id(master_client.master_id, master_client.client_id, msg.message_id)
        return msg.message_id

    # Try to edit existing message
    if master_client.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=master_client.home_message_id,
                text=text,
                reply_markup=keyboard
            )
            return master_client.home_message_id
        except TelegramBadRequest as e:
            # "message is not modified" - no need to send new message
            if "message is not modified" in str(e):
                return master_client.home_message_id
            # Otherwise message was deleted or not found - send new

    # Send new message
    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    await save_client_home_message_id(master_client.master_id, master_client.client_id, msg.message_id)
    return msg.message_id


async def edit_home_message(callback: CallbackQuery, text: str, keyboard) -> None:
    """Edit the home message with new content."""
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass


async def get_client_context(tg_id: int, master_id: int = None) -> tuple:
    """Get client, master, and master_client for a user.

    If master_id specified → use that master.
    If client has 1 master → use that one (backward compat).
    If client has multiple and no master_id → return (client, None, None).
    """
    client = await get_client_by_tg_id(tg_id)
    if not client:
        return None, None, None

    masters = await get_all_client_masters_by_tg_id(tg_id)
    if not masters:
        return client, None, None

    if master_id:
        entry = next((m for m in masters if m["master_id"] == master_id), None)
        if not entry:
            return client, None, None
    elif len(masters) == 1:
        master_id = masters[0]["master_id"]
    else:
        # Multiple masters, no selection — caller must handle
        return client, None, None

    master = await get_master_by_id(master_id)
    if not master:
        return client, None, None

    master_client = await get_master_client(master_id, client.id)
    return client, master, master_client


async def show_master_select(bot: Bot, tg_id: int, chat_id: int) -> None:
    """Show inline keyboard for selecting active master."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    masters = await get_all_client_masters_by_tg_id(tg_id)
    if not masters:
        await bot.send_message(chat_id, "Вы не привязаны ни к одному мастеру.")
        return

    buttons = [
        [InlineKeyboardButton(
            text=f"{m['master_name']}" + (f" · {m['sphere']}" if m.get('sphere') else ""),
            callback_data=f"select_master:{m['master_id']}",
        )]
        for m in masters
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(
        chat_id,
        "👥 У вас несколько мастеров. Выберите:",
        reply_markup=keyboard,
    )


class HomeButtonMiddleware(BaseMiddleware):
    """Middleware to intercept Home button before any FSM handlers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Only process text messages with "Home" button
        if isinstance(event, Message) and event.text and event.text == "🏠 Домой":
            bot: Bot = data["bot"]
            state: FSMContext = data["state"]
            tg_id = event.from_user.id

            client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
            if client and master and master_client:
                await state.clear()
                try:
                    await event.delete()
                except TelegramBadRequest:
                    pass
                await show_home(bot, client, master, master_client, event.chat.id, force_new=True)
            else:
                # Not registered - show message
                await event.answer("Вы не зарегистрированы. Перейдите по ссылке от мастера.")
            return  # Always stop propagation for "Home" button

        return await handler(event, data)


# =============================================================================
# Start and Home Commands
# =============================================================================


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /start command."""
    # Delete command message
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    tg_id = message.from_user.id

    # Check if already registered
    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if client and master and master_client:
        await state.clear()
        # Show home menu (force_new to show at bottom of chat)
        await show_home(bot, client, master, master_client, message.chat.id, force_new=True)
        return

    # Multi-master: registered but no master selected
    if client and not master:
        masters = await get_all_client_masters_by_tg_id(tg_id)
        if masters:
            await show_master_select(bot, tg_id, message.chat.id)
            return

    # Extract invite token
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await bot.send_message(
            message.chat.id,
            "👋 Добро пожаловать!\n\n"
            "Для регистрации нужна ссылка от вашего мастера.\n"
            "Попросите мастера отправить вам персональную ссылку.",
            reply_markup=home_reply_kb()
        )
        return

    invite_token = args[1].strip()

    # Find master
    master = await get_master_by_invite_token(invite_token)
    if not master:
        await bot.send_message(
            message.chat.id,
            "❌ Ссылка недействительна.\n\n"
            "Попросите мастера отправить вам актуальную ссылку."
        )
        return

    # Store master_id for registration
    await state.update_data(master_id=master.id)

    # Show consent screen
    await bot.send_message(
        message.chat.id,
        "Привет 👋\n\n"
        "Для регистрации нам нужно ваше согласие на обработку персональных данных.\n\n"
        "Мы собираем: имя, телефон, дату рождения (опционально).\n"
        "Данные используются только для записи и бонусной программы.\n\n"
        '📜 <a href="https://crmfit.ru/privacy">Политика конфиденциальности</a>',
        reply_markup=consent_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await state.set_state(ClientRegistration.consent)


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /support command."""
    # Delete command message
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    tg_id = message.from_user.id
    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))

    if not client or not master or not master_client:
        await message.answer("Вы не зарегистрированы. Перейдите по ссылке от мастера.")
        return

    text = (
        "📞 <b>Поддержка</b>\n\n"
        "По вопросам технической поддержки и разработки ботов:\n\n"
        "Telegram: @pastushenko12\n"
        "E-mail: copypast.pe@gmail.com"
    )

    # Edit home message
    if master_client.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master_client.home_message_id,
                text=text,
                reply_markup=client_home_kb(),
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            msg = await bot.send_message(message.chat.id, text, reply_markup=client_home_kb(), parse_mode="HTML")
            await save_client_home_message_id(master.id, client.id, msg.message_id)
    else:
        msg = await bot.send_message(message.chat.id, text, reply_markup=client_home_kb(), parse_mode="HTML")
        await save_client_home_message_id(master.id, client.id, msg.message_id)


@router.message(Command("delete_me"))
async def cmd_delete_me(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /delete_me command - request data deletion."""
    # Delete command message
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    tg_id = message.from_user.id

    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if not client or not master or not master_client:
        await bot.send_message(message.chat.id, "Вы не зарегистрированы в системе.")
        return

    await state.set_state(ClientDeletion.confirm)
    await state.update_data(client_id=client.id)

    text = (
        "⚠️ <b>Удаление данных</b>\n\n"
        "Вы уверены, что хотите удалить свои персональные данные?\n\n"
        "Будут удалены:\n"
        "• Имя\n"
        "• Телефон\n"
        "• Дата рождения\n"
        "• Привязка к Telegram\n\n"
        "История заказов сохранится в анонимизированном виде для учёта мастера.\n\n"
        "Это действие необратимо!"
    )

    # Edit home message
    if master_client.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master_client.home_message_id,
                text=text,
                reply_markup=delete_confirm_kb(),
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            msg = await bot.send_message(message.chat.id, text, reply_markup=delete_confirm_kb(), parse_mode="HTML")
            await save_client_home_message_id(master.id, client.id, msg.message_id)
    else:
        msg = await bot.send_message(message.chat.id, text, reply_markup=delete_confirm_kb(), parse_mode="HTML")
        await save_client_home_message_id(master.id, client.id, msg.message_id)


@router.callback_query(F.data == "delete:confirm")
async def delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm data deletion — stateless lookup by tg_id."""
    tg_id = callback.from_user.id
    client, _, _ = await get_client_context(tg_id, _active_masters.get(tg_id))

    if client:
        await anonymize_client(client.id)

    await state.clear()
    await callback.message.edit_text(
        "✅ Ваши данные удалены.\n\n"
        "Спасибо, что были с нами!"
    )
    await callback.answer()


@router.callback_query(F.data == "delete:cancel")
async def delete_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel data deletion."""
    await state.clear()

    tg_id = callback.from_user.id
    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))

    if client and master and master_client:
        text = await build_home_text(client, master, master_client)
        await callback.message.edit_text(text, reply_markup=home_client_kb())
    else:
        await callback.message.edit_text("Отменено.")

    await callback.answer()


# =============================================================================
# Consent Handlers
# =============================================================================

@router.callback_query(ClientRegistration.consent, F.data == "consent:agree")
async def consent_agree(callback: CallbackQuery, state: FSMContext) -> None:
    """User agreed to privacy policy."""
    # Store consent timestamp
    await state.update_data(consent_given_at=datetime.now().isoformat())

    await callback.message.edit_text(
        "✅ Спасибо за согласие!\n\n"
        "📝 Как вас зовут?"
    )
    await state.set_state(ClientRegistration.name)
    await callback.answer()


@router.callback_query(ClientRegistration.consent, F.data == "consent:decline")
async def consent_decline(callback: CallbackQuery, state: FSMContext) -> None:
    """User declined privacy policy."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Вы отказались от обработки данных.\n\n"
        "К сожалению, без согласия регистрация невозможна.\n"
        "Если передумаете — просто перейдите по ссылке от мастера снова."
    )
    await callback.answer()


# =============================================================================
# Registration FSM
# =============================================================================

@router.message(ClientRegistration.name)
async def reg_name(message: Message, state: FSMContext) -> None:
    """Step 1: Save name."""
    name = message.text.strip()[:100]
    await state.update_data(name=name)

    await message.answer(
        f"Приятно познакомиться, {name}!\n\n"
        "📱 Поделитесь своим номером телефона.\n"
        "Это нужно для связи с мастером.",
        reply_markup=share_contact_kb()
    )
    await state.set_state(ClientRegistration.phone)


@router.message(ClientRegistration.phone, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext) -> None:
    """Step 2: Save phone from contact."""
    phone = normalize_phone(message.contact.phone_number) or format_phone(message.contact.phone_number)
    await state.update_data(phone=phone)

    await message.answer(
        "🎂 Когда у вас день рождения?\n"
        "(в формате ДД.ММ или ДД.ММ.ГГГГ)\n\n"
        "Мастер сможет поздравить вас и начислить бонусы!",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer("Или пропустите этот шаг:", reply_markup=skip_kb())
    await state.set_state(ClientRegistration.birthday)


@router.message(ClientRegistration.phone)
async def reg_phone_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 2: Save phone from text."""
    import asyncio

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    # Validate and normalize phone
    phone = normalize_phone(message.text.strip())
    if not phone:
        error_msg = await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Неверный формат номера. Введите с кодом страны: +7..., +995..., +380..."
        )
        await asyncio.sleep(2)
        try:
            await error_msg.delete()
        except TelegramBadRequest:
            pass
        return

    await state.update_data(phone=phone)

    await message.answer(
        "🎂 Когда у вас день рождения?\n"
        "(в формате ДД.ММ или ДД.ММ.ГГГГ)\n\n"
        "Мастер сможет поздравить вас и начислить бонусы!",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer("Или пропустите этот шаг:", reply_markup=skip_kb())
    await state.set_state(ClientRegistration.birthday)


@router.message(ClientRegistration.birthday)
async def reg_birthday(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 3: Save birthday."""
    birthday = parse_date(message.text)
    if birthday:
        await state.update_data(birthday=birthday.isoformat())
    else:
        await state.update_data(birthday=None)

    await complete_registration(message, state, bot)


@router.callback_query(ClientRegistration.birthday, F.data == "skip")
async def reg_birthday_skip(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Step 3: Skip birthday."""
    await state.update_data(birthday=None)
    await complete_registration(callback.message, state, bot, edit=True)
    await callback.answer()


async def complete_registration(message: Message, state: FSMContext, bot: Bot, edit: bool = False) -> None:
    """Complete client registration."""
    data = await state.get_data()
    tg_id = message.chat.id
    master_id = data["master_id"]

    # Check if client exists by phone
    phone = data.get("phone")
    existing_client = None
    if phone:
        existing_client = await get_client_by_phone(phone)

    if existing_client:
        await update_client(existing_client.id, tg_id=tg_id, name=data["name"])
        if data.get("birthday"):
            await update_client(existing_client.id, birthday=data["birthday"])
        client = existing_client
        client.tg_id = tg_id
        client.name = data["name"]
    else:
        client = await create_client(
            tg_id=tg_id,
            name=data["name"],
            phone=phone,
            birthday=data.get("birthday"),
            registered_via=master_id,
        )

    # Save consent timestamp
    if data.get("consent_given_at"):
        await update_client_consent(client.id, data["consent_given_at"])

    # Link to master
    master_client = await link_client_to_master(master_id, client.id)
    master = await get_master_by_id(master_id)

    await state.clear()

    # "Регистрация завершена!" — with reply keyboard, no separate house message
    success_text = "✅ Регистрация завершена!"
    if edit:
        await message.edit_text(success_text)
        await message.answer("🏠", reply_markup=home_reply_kb())
    else:
        await message.answer(success_text, reply_markup=home_reply_kb())

    # Build welcome home text (shown until user navigates back)
    home_text = None
    if master.bonus_welcome and master.bonus_welcome > 0:
        bonus_amount = await accrue_welcome_bonus(master.id, client.id)
        if bonus_amount > 0:
            master_client = await get_master_client(master.id, client.id)
            home_text = render_bonus_message(
                template=master.welcome_message,
                default=DEFAULT_WELCOME_MESSAGE,
                client_name=client.name,
                master_name=master.name,
                bonus_amount=bonus_amount,
                balance=master_client.bonus_balance,
                currency=get_currency_symbol(master.currency),
            )

    # Show home screen: welcome text if configured, otherwise normal home text
    if home_text:
        msg = await bot.send_message(
            message.chat.id,
            home_text,
            reply_markup=home_client_kb(),
        )
        await save_client_home_message_id(master_client.master_id, master_client.client_id, msg.message_id)
    else:
        await show_home(bot, client, master, master_client, message.chat.id)


# =============================================================================
# Navigation: Home
# =============================================================================

@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    """Return to home screen."""
    # Clear any active FSM state
    await state.clear()

    tg_id = callback.from_user.id

    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if not client or not master or not master_client:
        await callback.answer("Ошибка")
        return

    text = await build_home_text(client, master, master_client)
    all_masters = await get_all_client_masters_by_tg_id(client.tg_id)
    await edit_home_message(callback, text, home_client_kb(multi_master=len(all_masters) > 1))
    await callback.answer()


@router.callback_query(F.data.startswith("select_master:"))
async def cb_select_master(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    """Handle master selection from multi-master picker."""
    tg_id = callback.from_user.id
    master_id = int(callback.data.split(":")[1])

    _active_masters[tg_id] = master_id

    client, master, master_client = await get_client_context(tg_id, master_id)
    if not client or not master or not master_client:
        await callback.answer("Ошибка при выборе мастера")
        return

    await callback.message.delete()
    await show_home(bot, client, master, master_client, callback.message.chat.id, force_new=True)
    await callback.answer()


@router.callback_query(F.data == "change_master")
async def cb_change_master(callback: CallbackQuery, bot: Bot) -> None:
    """Show master selection screen."""
    tg_id = callback.from_user.id
    await callback.message.delete()
    await show_master_select(bot, tg_id, callback.message.chat.id)
    await callback.answer()


# =============================================================================
# Bonuses Section
# =============================================================================

@router.callback_query(F.data == "bonuses")
async def cb_bonuses(callback: CallbackQuery) -> None:
    """Show bonuses."""
    tg_id = callback.from_user.id

    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if not client or not master:
        await callback.answer("Ошибка")
        return

    curr = get_currency_symbol(master.currency)
    bonus_log = await get_client_bonus_log(master.id, client.id, limit=10)

    if bonus_log:
        log_text = "\n".join(
            f"• {b.get('created_at', '')[:10] if b.get('created_at') else '—'} "
            f"{'+' if b.get('amount', 0) > 0 else ''}{b.get('amount', 0)} — "
            f"{b.get('comment', 'операция')}"
            for b in bonus_log
        )
    else:
        log_text = "Операций пока нет"

    text = (
        "💰 Мои бонусы\n"
        "━━━━━━━━━━━━━━━\n"
        f"Баланс: {master_client.bonus_balance} {curr}\n\n"
        f"{log_text}\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, client_bonuses_kb())
    await callback.answer()


# =============================================================================
# History Section
# =============================================================================

@router.callback_query(F.data == "history")
async def cb_history(callback: CallbackQuery) -> None:
    """Show order history."""
    tg_id = callback.from_user.id

    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if not client or not master:
        await callback.answer("Ошибка")
        return

    curr = get_currency_symbol(master.currency)
    orders = await get_client_orders(master.id, client.id, limit=20)

    if orders:
        orders_text = "\n".join(
            f"• {o.get('scheduled_at', '')[:10] if o.get('scheduled_at') else '—'} — "
            f"{o.get('services', '—')[:25]} | {o.get('amount_total', 0)} {curr}"
            for o in orders
            if o.get('status') == 'done'
        )
        if not orders_text:
            orders_text = "Выполненных заказов пока нет"
    else:
        orders_text = "История пуста"

    text = (
        "📋 История визитов\n"
        "━━━━━━━━━━━━━━━\n"
        f"{orders_text}\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, client_bot_history_kb())
    await callback.answer()


# =============================================================================
# Promos Section
# =============================================================================

@router.callback_query(F.data == "promos")
async def cb_promos(callback: CallbackQuery) -> None:
    """Show active promos."""
    tg_id = callback.from_user.id

    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if not client or not master:
        await callback.answer("Ошибка")
        return

    campaigns = await get_active_campaigns(master.id)

    if campaigns:
        promos_text = ""
        for c in campaigns:
            active_to = c.active_to
            if active_to:
                try:
                    d = date.fromisoformat(str(active_to))
                    until_text = f"До {d.day} {MONTHS_RU[d.month]}"
                except Exception:
                    until_text = ""
            else:
                until_text = ""

            promos_text += f"🔥 {c.title or 'Акция'}\n"
            promos_text += f"{c.text}\n"
            if until_text:
                promos_text += f"{until_text}\n"
            promos_text += "\n"
    else:
        promos_text = "Акций пока нет. Следите за обновлениями!"

    text = (
        "🎁 Акции\n"
        "━━━━━━━━━━━━━━━\n"
        f"{promos_text.strip()}\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, client_promos_kb())
    await callback.answer()


# =============================================================================
# Master Info Section
# =============================================================================

@router.callback_query(F.data == "master_info")
async def cb_master_info(callback: CallbackQuery) -> None:
    """Show master info."""
    tg_id = callback.from_user.id

    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if not client or not master:
        await callback.answer("Ошибка")
        return

    text = (
        "👨‍🔧 Ваш мастер\n"
        "━━━━━━━━━━━━━━━\n"
        f"{master.name}\n"
        f"{master.sphere or ''}\n\n"
        f"📞 {master.contacts or '—'}\n"
        f"🌐 {master.socials or '—'}\n"
        f"🕐 {master.work_hours or '—'}\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, client_master_info_kb())
    await callback.answer()


# =============================================================================
# Notifications Section
# =============================================================================

@router.callback_query(F.data == "notifications")
async def cb_notifications(callback: CallbackQuery) -> None:
    """Show notifications settings."""
    tg_id = callback.from_user.id

    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if not client or not master or not master_client:
        await callback.answer("Ошибка")
        return

    text = (
        "🔔 Настройки уведомлений\n"
        "━━━━━━━━━━━━━━━\n"
        "(Уведомления о статусе заказа\n"
        "отключить нельзя)\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, client_notifications_back_kb(
        master_client.notify_24h,
        master_client.notify_1h,
        master_client.notify_marketing,
        master_client.notify_promos,
    ))
    await callback.answer()


@router.callback_query(F.data.startswith("notifications:toggle:"))
async def cb_notifications_toggle(callback: CallbackQuery) -> None:
    """Toggle notification setting."""
    tg_id = callback.from_user.id

    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if not client or not master or not master_client:
        await callback.answer("Ошибка")
        return

    field = callback.data.split(":")[2]

    # Toggle in DB
    new_value = await toggle_client_notification(master.id, client.id, field)

    # Update master_client object
    setattr(master_client, field, new_value)

    # Update keyboard
    text = (
        "🔔 Настройки уведомлений\n"
        "━━━━━━━━━━━━━━━\n"
        "(Уведомления о статусе заказа\n"
        "отключить нельзя)\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, client_notifications_back_kb(
        master_client.notify_24h,
        master_client.notify_1h,
        master_client.notify_marketing,
        master_client.notify_promos,
    ))
    await callback.answer("Сохранено")


@router.callback_query(F.data == "client_settings")
async def cb_client_settings(callback: CallbackQuery) -> None:
    """Show client settings menu."""
    text = (
        "⚙️ Настройки\n"
        "━━━━━━━━━━━━━━━"
    )
    await edit_home_message(callback, text, client_settings_kb())
    await callback.answer()


@router.callback_query(F.data == "client_support")
async def cb_client_support(callback: CallbackQuery) -> None:
    """Show support info."""
    text = (
        "💬 Поддержка\n"
        "━━━━━━━━━━━━━━━\n"
        "По вопросам работы бота:\n\n"
        "Telegram: @pastushenko12\n"
        "E-mail: copypast.pe@gmail.com"
    )
    await edit_home_message(callback, text, back_kb("client_settings"))
    await callback.answer()


@router.callback_query(F.data == "client_delete_profile")
async def cb_client_delete_profile(callback: CallbackQuery, state: FSMContext) -> None:
    """Start profile deletion flow from settings."""
    tg_id = callback.from_user.id
    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if not client or not master_client:
        await callback.answer("Ошибка")
        return

    await state.set_state(ClientDeletion.confirm)
    await state.update_data(client_id=client.id)

    text = (
        "⚠️ Удаление данных\n"
        "━━━━━━━━━━━━━━━\n"
        "Будут удалены:\n"
        "• Имя\n"
        "• Телефон\n"
        "• Дата рождения\n"
        "• Привязка к Telegram\n\n"
        "История заказов сохранится анонимно.\n\n"
        "Это действие необратимо!"
    )
    await edit_home_message(callback, text, delete_confirm_kb())
    await callback.answer()


# =============================================================================
# Order Request FSM
# =============================================================================

@router.callback_query(F.data == "order_request")
async def cb_order_request(callback: CallbackQuery, state: FSMContext) -> None:
    """Start order request flow."""
    tg_id = callback.from_user.id
    client = await get_client_by_tg_id(tg_id)
    if not client:
        await callback.answer("Клиент не найден")
        return

    master_client = await get_master_client_by_client_tg_id(tg_id)
    if not master_client:
        await callback.answer("Мастер не найден")
        return

    # Get master's services
    services = await get_master_services_for_client(master_client.master_id)

    await state.update_data(
        master_id=master_client.master_id,
        client_id=client.id
    )
    await state.set_state(OrderRequestFSM.service)

    text = "📞 Заявка на заказ\n\nВыберите услугу:"
    await edit_home_message(callback, text, order_request_services_kb(services))
    await callback.answer()


@router.callback_query(F.data.startswith("order_req:service:"), OrderRequestFSM.service)
async def cb_order_service_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle service selection."""
    service_id = callback.data.split(":")[-1]

    if service_id == "other":
        await state.set_state(OrderRequestFSM.custom_service)
        text = "📝 Введите название услуги:"
        await edit_home_message(callback, text, question_cancel_kb())
    else:
        # Get service name by ID
        data = await state.get_data()
        services = await get_master_services_for_client(data["master_id"])
        service_name = next((s["name"] for s in services if s["id"] == int(service_id)), "Услуга")

        await state.update_data(service_name=service_name)
        await state.set_state(OrderRequestFSM.comment)

        text = (
            "💬 Добавьте комментарий (необязательно):\n"
            "Например: площадь квартиры, адрес, пожелания"
        )
        await edit_home_message(callback, text, order_request_comment_kb())

    await callback.answer()


@router.message(OrderRequestFSM.custom_service)
async def fsm_order_custom_service(message: Message, state: FSMContext) -> None:
    """Handle custom service name input."""
    service_name = message.text.strip()
    if not service_name:
        await message.answer("Введите название услуги:", reply_markup=question_cancel_kb())
        return

    await state.update_data(service_name=service_name)
    await state.set_state(OrderRequestFSM.comment)

    data = await state.get_data()
    home_message_id = data.get("home_message_id")

    text = (
        "💬 Добавьте комментарий (необязательно):\n"
        "Например: площадь квартиры, адрес, пожелания"
    )

    if home_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=home_message_id,
                text=text,
                reply_markup=order_request_comment_kb()
            )
        except TelegramBadRequest:
            await message.answer(text, reply_markup=order_request_comment_kb())
    else:
        await message.answer(text, reply_markup=order_request_comment_kb())


@router.callback_query(F.data == "order_req:skip_comment", OrderRequestFSM.comment)
async def cb_order_skip_comment(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip comment step."""
    await state.update_data(comment=None)
    await show_order_confirmation(callback, state)
    await callback.answer()


@router.message(OrderRequestFSM.comment)
async def fsm_order_comment(message: Message, state: FSMContext) -> None:
    """Handle comment input."""
    comment = message.text.strip()
    await state.update_data(comment=comment if comment else None)

    # Show confirmation
    data = await state.get_data()
    home_message_id = data.get("home_message_id")
    service_name = data.get("service_name", "")
    comment_text = comment if comment else "—"

    text = (
        f"📋 Ваша заявка:\n\n"
        f"🛠 Услуга: {service_name}\n"
        f"💬 Комментарий: {comment_text}"
    )

    await state.set_state(OrderRequestFSM.confirm)

    if home_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=home_message_id,
                text=text,
                reply_markup=order_request_confirm_kb()
            )
        except TelegramBadRequest:
            await message.answer(text, reply_markup=order_request_confirm_kb())
    else:
        await message.answer(text, reply_markup=order_request_confirm_kb())


async def show_order_confirmation(callback: CallbackQuery, state: FSMContext) -> None:
    """Show order request confirmation screen."""
    data = await state.get_data()
    service_name = data.get("service_name", "")
    comment = data.get("comment")
    comment_text = comment if comment else "—"

    text = (
        f"📋 Ваша заявка:\n\n"
        f"🛠 Услуга: {service_name}\n"
        f"💬 Комментарий: {comment_text}"
    )

    await state.set_state(OrderRequestFSM.confirm)
    await edit_home_message(callback, text, order_request_confirm_kb())


@router.callback_query(F.data == "order_req:confirm", OrderRequestFSM.confirm)
async def cb_order_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm and send order request."""
    global master_bot
    from aiogram.exceptions import TelegramForbiddenError

    data = await state.get_data()
    master_id = data.get("master_id")
    client_id = data.get("client_id")
    service_name = data.get("service_name", "")
    comment = data.get("comment")

    # Save to database
    await save_inbound_request(
        master_id=master_id,
        client_id=client_id,
        type="order_request",
        text=comment,
        service_name=service_name
    )

    # Get client and master data
    tg_id = callback.from_user.id
    client = await get_client_by_tg_id(tg_id)
    master = await get_master_by_id(master_id)

    # Send notification to master
    username = callback.from_user.username
    username_text = f"@{username}" if username else f"tg://user?id={tg_id}"

    notify_text = (
        f"🛎 Новая заявка на заказ!\n\n"
        f"👤 {client.name}\n"
        f"📞 {client.phone or '—'}\n"
        f"✈️ {username_text}\n"
        f"🛠 Услуга: {service_name}"
    )
    if comment:
        notify_text += f"\n💬 {comment}"

    master_blocked = False
    if master_bot:
        try:
            await master_bot.send_message(master.tg_id, notify_text)
        except TelegramForbiddenError:
            master_blocked = True
        except Exception as e:
            logger.error(f"Failed to notify master: {e}")

    await state.clear()

    # Show success to client
    if master_blocked:
        text = (
            "✅ Заявка отправлена!\n\n"
            "⚠️ К сожалению, мастер временно недоступен.\n"
            f"📞 Свяжитесь напрямую: {master.contacts or '—'}"
        )
    else:
        text = (
            "✅ Заявка отправлена!\n\n"
            "Мастер свяжется с вами в ближайшее время.\n"
            f"📞 {master.contacts or ''}"
        )

    await edit_home_message(callback, text, client_home_kb())
    await callback.answer()


# =============================================================================
# Question FSM
# =============================================================================

@router.callback_query(F.data == "question")
async def cb_question(callback: CallbackQuery, state: FSMContext) -> None:
    """Start question flow."""
    tg_id = callback.from_user.id
    client = await get_client_by_tg_id(tg_id)
    if not client:
        await callback.answer("Клиент не найден")
        return

    master_client = await get_master_client_by_client_tg_id(tg_id)
    if not master_client:
        await callback.answer("Мастер не найден")
        return

    await state.update_data(
        master_id=master_client.master_id,
        client_id=client.id
    )
    await state.set_state(QuestionFSM.text)

    text = "❓ Задать вопрос мастеру\n\nВведите ваш вопрос:"
    await edit_home_message(callback, text, question_cancel_kb())
    await callback.answer()


@router.message(QuestionFSM.text)
async def fsm_question_text(message: Message, state: FSMContext) -> None:
    """Handle question text input."""
    global master_bot
    from aiogram.exceptions import TelegramForbiddenError

    question_text = message.text.strip()
    if not question_text:
        await message.answer("Введите ваш вопрос:", reply_markup=question_cancel_kb())
        return

    data = await state.get_data()
    master_id = data.get("master_id")
    client_id = data.get("client_id")

    # Save to database
    await save_inbound_request(
        master_id=master_id,
        client_id=client_id,
        type="question",
        text=question_text
    )

    # Get client and master data
    tg_id = message.from_user.id
    client = await get_client_by_tg_id(tg_id)
    master = await get_master_by_id(master_id)

    # Send notification to master
    username = message.from_user.username
    if username:
        username_text = f"@{username}"
    else:
        username_text = f"[{client.name}](tg://user?id={tg_id})"

    notify_text = (
        f"❓ Вопрос от клиента\n\n"
        f"👤 {client.name}\n"
        f"📞 {client.phone or '—'}\n"
        f"✈️ {username_text}\n\n"
        f"Вопрос:\n{question_text}"
    )

    master_blocked = False
    if master_bot:
        try:
            await master_bot.send_message(master.tg_id, notify_text, parse_mode="Markdown")
        except TelegramForbiddenError:
            master_blocked = True
        except Exception as e:
            logger.error(f"Failed to notify master: {e}")

    await state.clear()

    # Show success to client
    home_message_id = data.get("home_message_id")

    if master_blocked:
        text = (
            "✅ Вопрос отправлен!\n\n"
            "⚠️ К сожалению, мастер временно недоступен.\n"
            f"📞 Свяжитесь напрямую: {master.contacts or '—'}"
        )
    else:
        text = "✅ Вопрос отправлен!\n\nМастер ответит вам в личные сообщения."

    if home_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=home_message_id,
                text=text,
                reply_markup=client_home_kb()
            )
        except TelegramBadRequest:
            await message.answer(text, reply_markup=client_home_kb())
    else:
        await message.answer(text, reply_markup=client_home_kb())


# =============================================================================
# Media FSM
# =============================================================================

@router.callback_query(F.data == "media")
async def cb_media(callback: CallbackQuery, state: FSMContext) -> None:
    """Start media sending flow."""
    tg_id = callback.from_user.id
    client = await get_client_by_tg_id(tg_id)
    if not client:
        await callback.answer("Клиент не найден")
        return

    master_client = await get_master_client_by_client_tg_id(tg_id)
    if not master_client:
        await callback.answer("Мастер не найден")
        return

    await state.update_data(
        master_id=master_client.master_id,
        client_id=client.id
    )
    await state.set_state(MediaFSM.media)

    text = (
        "📸 Отправить фото или видео мастеру\n\n"
        "Например: фото объекта для оценки стоимости,\n"
        "видео поломки, фото до/после\n\n"
        "Отправьте фото или видео:"
    )
    await edit_home_message(callback, text, media_cancel_kb())
    await callback.answer()


@router.message(MediaFSM.media, F.photo)
async def fsm_media_photo(message: Message, state: FSMContext) -> None:
    """Handle photo upload."""
    file_id = message.photo[-1].file_id  # Get largest photo
    await state.update_data(file_id=file_id, media_type="photo")
    await state.set_state(MediaFSM.comment)

    data = await state.get_data()
    home_message_id = data.get("home_message_id")

    text = "💬 Добавьте комментарий (необязательно):"

    if home_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=home_message_id,
                text=text,
                reply_markup=media_comment_kb()
            )
        except TelegramBadRequest:
            await message.answer(text, reply_markup=media_comment_kb())
    else:
        await message.answer(text, reply_markup=media_comment_kb())


@router.message(MediaFSM.media, F.video)
async def fsm_media_video(message: Message, state: FSMContext) -> None:
    """Handle video upload."""
    file_id = message.video.file_id
    await state.update_data(file_id=file_id, media_type="video")
    await state.set_state(MediaFSM.comment)

    data = await state.get_data()
    home_message_id = data.get("home_message_id")

    text = "💬 Добавьте комментарий (необязательно):"

    if home_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=home_message_id,
                text=text,
                reply_markup=media_comment_kb()
            )
        except TelegramBadRequest:
            await message.answer(text, reply_markup=media_comment_kb())
    else:
        await message.answer(text, reply_markup=media_comment_kb())


@router.message(MediaFSM.media, F.document)
async def fsm_media_document(message: Message, state: FSMContext) -> None:
    """Handle document upload (in case client sends as file)."""
    file_id = message.document.file_id
    await state.update_data(file_id=file_id, media_type="document")
    await state.set_state(MediaFSM.comment)

    data = await state.get_data()
    home_message_id = data.get("home_message_id")

    text = "💬 Добавьте комментарий (необязательно):"

    if home_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=home_message_id,
                text=text,
                reply_markup=media_comment_kb()
            )
        except TelegramBadRequest:
            await message.answer(text, reply_markup=media_comment_kb())
    else:
        await message.answer(text, reply_markup=media_comment_kb())


@router.callback_query(F.data == "media:skip_comment", MediaFSM.comment)
async def cb_media_skip_comment(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip comment and send media."""
    await state.update_data(comment=None)
    await send_media_to_master(callback, state)
    await callback.answer()


@router.message(MediaFSM.comment)
async def fsm_media_comment(message: Message, state: FSMContext) -> None:
    """Handle comment for media."""
    comment = message.text.strip() if message.text else None
    await state.update_data(comment=comment)
    await send_media_to_master_from_message(message, state)


async def send_media_to_master(callback: CallbackQuery, state: FSMContext) -> None:
    """Send media to master from callback context."""
    global master_bot
    from aiogram.exceptions import TelegramForbiddenError
    from aiogram.types import BufferedInputFile
    import aiohttp

    data = await state.get_data()
    master_id = data.get("master_id")
    client_id = data.get("client_id")
    file_id = data.get("file_id")
    media_type = data.get("media_type")
    comment = data.get("comment")

    # Save to database
    await save_inbound_request(
        master_id=master_id,
        client_id=client_id,
        type="media",
        text=comment,
        file_id=file_id
    )

    # Get client and master data
    tg_id = callback.from_user.id
    client = await get_client_by_tg_id(tg_id)
    master = await get_master_by_id(master_id)

    # Build caption
    username = callback.from_user.username
    username_text = f"@{username}" if username else f"tg://user?id={tg_id}"

    caption = (
        f"📸 Медиа от клиента\n\n"
        f"👤 {client.name}\n"
        f"📞 {client.phone or '—'}\n"
        f"✈️ {username_text}"
    )
    if comment:
        caption += f"\n💬 {comment}"

    master_blocked = False
    if master_bot:
        try:
            # Download file from client_bot and re-upload to master_bot
            file_info = await callback.bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{CLIENT_BOT_TOKEN}/{file_info.file_path}"

            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    if resp.status == 200:
                        media_bytes = await resp.read()

                        if media_type == "photo":
                            await master_bot.send_photo(
                                master.tg_id,
                                photo=BufferedInputFile(media_bytes, filename="photo.jpg"),
                                caption=caption
                            )
                        elif media_type == "video":
                            await master_bot.send_video(
                                master.tg_id,
                                video=BufferedInputFile(media_bytes, filename="video.mp4"),
                                caption=caption
                            )
                        else:
                            await master_bot.send_document(
                                master.tg_id,
                                document=BufferedInputFile(media_bytes, filename="file"),
                                caption=caption
                            )
        except TelegramForbiddenError:
            master_blocked = True
        except Exception as e:
            logger.error(f"Failed to send media to master: {e}")

    await state.clear()

    # Show success to client
    if master_blocked:
        text = (
            "✅ Отправлено!\n\n"
            "⚠️ К сожалению, мастер временно недоступен.\n"
            f"📞 Свяжитесь напрямую: {master.contacts or '—'}"
        )
    else:
        text = "✅ Отправлено!\n\nМастер получил ваше фото/видео."

    await edit_home_message(callback, text, client_home_kb())


async def send_media_to_master_from_message(message: Message, state: FSMContext) -> None:
    """Send media to master from message context."""
    global master_bot
    from aiogram.exceptions import TelegramForbiddenError
    from aiogram.types import BufferedInputFile
    import aiohttp

    data = await state.get_data()
    master_id = data.get("master_id")
    client_id = data.get("client_id")
    file_id = data.get("file_id")
    media_type = data.get("media_type")
    comment = data.get("comment")
    home_message_id = data.get("home_message_id")

    # Save to database
    await save_inbound_request(
        master_id=master_id,
        client_id=client_id,
        type="media",
        text=comment,
        file_id=file_id
    )

    # Get client and master data
    tg_id = message.from_user.id
    client = await get_client_by_tg_id(tg_id)
    master = await get_master_by_id(master_id)

    # Build caption
    username = message.from_user.username
    username_text = f"@{username}" if username else f"tg://user?id={tg_id}"

    caption = (
        f"📸 Медиа от клиента\n\n"
        f"👤 {client.name}\n"
        f"📞 {client.phone or '—'}\n"
        f"✈️ {username_text}"
    )
    if comment:
        caption += f"\n💬 {comment}"

    master_blocked = False
    if master_bot:
        try:
            # Download file from client_bot and re-upload to master_bot
            file_info = await message.bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{CLIENT_BOT_TOKEN}/{file_info.file_path}"

            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    if resp.status == 200:
                        media_bytes = await resp.read()

                        if media_type == "photo":
                            await master_bot.send_photo(
                                master.tg_id,
                                photo=BufferedInputFile(media_bytes, filename="photo.jpg"),
                                caption=caption
                            )
                        elif media_type == "video":
                            await master_bot.send_video(
                                master.tg_id,
                                video=BufferedInputFile(media_bytes, filename="video.mp4"),
                                caption=caption
                            )
                        else:
                            await master_bot.send_document(
                                master.tg_id,
                                document=BufferedInputFile(media_bytes, filename="file"),
                                caption=caption
                            )
        except TelegramForbiddenError:
            master_blocked = True
        except Exception as e:
            logger.error(f"Failed to send media to master: {e}")

    await state.clear()

    # Show success to client
    if master_blocked:
        text = (
            "✅ Отправлено!\n\n"
            "⚠️ К сожалению, мастер временно недоступен.\n"
            f"📞 Свяжитесь напрямую: {master.contacts or '—'}"
        )
    else:
        text = "✅ Отправлено!\n\nМастер получил ваше фото/видео."

    if home_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=home_message_id,
                text=text,
                reply_markup=client_home_kb()
            )
        except TelegramBadRequest:
            await message.answer(text, reply_markup=client_home_kb())
    else:
        await message.answer(text, reply_markup=client_home_kb())


# =============================================================================
# Order Confirmation (from reminder)
# =============================================================================

@router.callback_query(F.data.startswith("confirm_order:"))
async def handle_order_confirmation(callback: CallbackQuery) -> None:
    """Handle order confirmation from 24h reminder."""
    global master_bot

    order_id = int(callback.data.split(":")[1])
    client_tg_id = callback.from_user.id

    # Get order data
    order = await get_order_for_confirmation(order_id, client_tg_id)

    if not order:
        await callback.answer("Заказ не найден")
        return

    if order["status"] not in ("new", "confirmed"):
        await callback.answer("Заказ уже обработан")
        return

    # Parse scheduled_at for display
    scheduled_at = datetime.fromisoformat(order["scheduled_at"])
    day = scheduled_at.day
    month = MONTHS_RU[scheduled_at.month]
    time_str = scheduled_at.strftime("%H:%M")

    services = order.get("services") or "—"
    address = order.get("address") or "—"
    master_name = order.get("master_name") or "—"
    master_contacts = order.get("master_contacts") or "—"

    # Mark order as confirmed by client
    await mark_order_confirmed_by_client(order_id)

    # Update client message - remove button, add confirmation text
    new_text = (
        f"🔔 Напоминание о записи\n\n"
        f"📅 {day} {month}, {time_str}\n"
        f"📍 {address}\n"
        f"🛠 {services}\n\n"
        f"Мастер: {master_name}\n"
        f"📞 {master_contacts}\n\n"
        f"✅ Вы подтвердили запись"
    )

    try:
        await callback.message.edit_text(text=new_text, reply_markup=None)
    except TelegramBadRequest:
        pass

    # Send notification to master
    if master_bot and order.get("master_tg_id"):
        try:
            client_name = order.get("client_name") or "Клиент"
            master_text = (
                f"✅ Клиент подтвердил запись!\n\n"
                f"👤 {client_name}\n"
                f"📅 {day} {month}, {time_str}\n"
                f"📍 {address}\n"
                f"🛠 {services}"
            )
            await master_bot.send_message(
                chat_id=order["master_tg_id"],
                text=master_text
            )
        except Exception as e:
            logger.error(f"Failed to notify master about confirmation: {e}")

    await callback.answer("Запись подтверждена!")


# =============================================================================
# Order Reschedule from Reminder (client-side)
# =============================================================================

@router.callback_query(F.data.startswith("reschedule_order:"))
async def handle_reschedule_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Start reschedule flow from 24h reminder."""
    order_id = int(callback.data.split(":")[1])
    client_tg_id = callback.from_user.id

    # Get order data
    order = await get_order_for_confirmation(order_id, client_tg_id)

    if not order:
        await callback.answer("Заказ не найден")
        return

    if order["status"] not in ("new", "confirmed"):
        await callback.answer("Заказ уже обработан")
        return

    # Store order data in state
    await state.update_data(
        reschedule_order_id=order_id,
        reschedule_old_dt=order["scheduled_at"],
        reschedule_master_id=order["master_id"],
        reschedule_master_tg_id=order["master_tg_id"],
        reschedule_address=order.get("address"),
        reschedule_services=order.get("services"),
        reschedule_master_name=order.get("master_name"),
        reschedule_master_contacts=order.get("master_contacts"),
    )

    # Show calendar
    today = date.today()
    text = "📅 Выберите новую дату:"
    await callback.message.edit_text(
        text=text,
        reply_markup=client_reschedule_calendar_kb(today.year, today.month)
    )
    await state.set_state(ClientRescheduleOrder.date)
    await callback.answer()


@router.callback_query(ClientRescheduleOrder.date, F.data.regexp(r"^client_resched:cal:\d+:\d+$"))
async def client_reschedule_calendar_nav(callback: CallbackQuery, state: FSMContext) -> None:
    """Navigate calendar for reschedule."""
    parts = callback.data.split(":")
    year = int(parts[2])
    month = int(parts[3])

    text = "📅 Выберите новую дату:"
    await callback.message.edit_text(
        text=text,
        reply_markup=client_reschedule_calendar_kb(year, month)
    )
    await callback.answer()


@router.callback_query(ClientRescheduleOrder.date, F.data.startswith("client_resched:date:"))
async def client_reschedule_select_date(callback: CallbackQuery, state: FSMContext) -> None:
    """Select new date for order."""
    date_str = callback.data.split(":")[2]
    await state.update_data(reschedule_new_date=date_str)

    text = "⏰ Выберите время:"
    await callback.message.edit_text(text=text, reply_markup=client_reschedule_hour_kb())
    await state.set_state(ClientRescheduleOrder.hour)
    await callback.answer()


@router.callback_query(ClientRescheduleOrder.hour, F.data.startswith("client_resched:hour:"))
async def client_reschedule_select_hour(callback: CallbackQuery, state: FSMContext) -> None:
    """Select new hour for order."""
    hour = int(callback.data.split(":")[2])
    await state.update_data(reschedule_new_hour=hour)

    text = "⏰ Выберите минуты:"
    await callback.message.edit_text(
        text=text,
        reply_markup=client_reschedule_minutes_kb(hour)
    )
    await state.set_state(ClientRescheduleOrder.minutes)
    await callback.answer()


@router.callback_query(ClientRescheduleOrder.minutes, F.data.startswith("client_resched:minutes:"))
async def client_reschedule_select_minutes(callback: CallbackQuery, state: FSMContext) -> None:
    """Select new minutes, show confirmation."""
    minutes = int(callback.data.split(":")[2])
    await state.update_data(reschedule_new_minutes=minutes)

    data = await state.get_data()
    new_date_str = data.get("reschedule_new_date")
    new_hour = data.get("reschedule_new_hour")
    old_dt = datetime.fromisoformat(data.get("reschedule_old_dt"))
    new_dt = datetime.fromisoformat(f"{new_date_str}T{new_hour:02d}:{minutes:02d}:00")

    old_day = old_dt.day
    old_month = MONTHS_RU[old_dt.month]
    old_time = old_dt.strftime("%H:%M")

    new_day = new_dt.day
    new_month = MONTHS_RU[new_dt.month]
    new_time = new_dt.strftime("%H:%M")

    text = (
        f"📅 Перенос записи\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Было: {old_time} | {old_day} {old_month}\n"
        f"Станет: {new_time} | {new_day} {new_month}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Подтвердить перенос?"
    )

    await callback.message.edit_text(text=text, reply_markup=client_reschedule_confirm_kb())
    await state.set_state(ClientRescheduleOrder.confirm)
    await callback.answer()


@router.callback_query(ClientRescheduleOrder.confirm, F.data == "client_resched:confirm:yes")
async def client_reschedule_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Execute order reschedule from client side."""
    global master_bot

    data = await state.get_data()
    order_id = data.get("reschedule_order_id")
    new_date_str = data.get("reschedule_new_date")
    new_hour = data.get("reschedule_new_hour")
    new_minutes = data.get("reschedule_new_minutes")
    master_tg_id = data.get("reschedule_master_tg_id")
    master_name = data.get("reschedule_master_name")
    master_contacts = data.get("reschedule_master_contacts")
    address = data.get("reschedule_address")
    services = data.get("reschedule_services")

    new_dt = datetime.fromisoformat(f"{new_date_str}T{new_hour:02d}:{new_minutes:02d}:00")

    # Update order schedule
    await update_order_schedule(order_id, new_dt)

    # Check if new time is within 24 hours - auto-confirm, otherwise reset for reconfirmation
    now = datetime.now()
    hours_until = (new_dt - now).total_seconds() / 3600

    if hours_until <= 24:
        # Auto-confirm: within 24h, no need for new reminder cycle
        await mark_order_confirmed_by_client(order_id)
    else:
        # Reset flags for new reminder cycle
        await reset_order_for_reconfirmation(order_id)

    await state.clear()

    # Format new date for display
    new_day = new_dt.day
    new_month = MONTHS_RU[new_dt.month]
    new_time = new_dt.strftime("%H:%M")

    # Get client info
    tg_id = callback.from_user.id
    client = await get_client_by_tg_id(tg_id)

    # Show success to client
    text = (
        f"✅ Запись перенесена!\n\n"
        f"📅 {new_day} {new_month}, {new_time}\n"
        f"📍 {address or '—'}\n"
        f"🛠 {services or '—'}\n\n"
        f"Мастер: {master_name}\n"
        f"📞 {master_contacts or '—'}"
    )

    await callback.message.edit_text(text=text, reply_markup=None)

    # Notify master
    if master_bot and master_tg_id:
        try:
            master_text = (
                f"📅 Клиент перенёс запись!\n\n"
                f"👤 {client.name if client else '—'}\n"
                f"📅 Новая дата: {new_day} {new_month}, {new_time}\n"
                f"📍 {address or '—'}\n"
                f"🛠 {services or '—'}"
            )
            await master_bot.send_message(chat_id=master_tg_id, text=master_text)
        except Exception as e:
            logger.error(f"Failed to notify master about reschedule: {e}")

    await callback.answer("Запись перенесена!")


@router.callback_query(F.data == "client_resched:cancel")
async def client_reschedule_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel reschedule flow."""
    await state.clear()
    await callback.message.edit_text(
        text="❌ Перенос отменён.\n\nВаша запись осталась без изменений.",
        reply_markup=None
    )
    await callback.answer()


# =============================================================================
# Order Cancel from Reminder (client-side)
# =============================================================================

@router.callback_query(F.data.startswith("cancel_order:"))
async def handle_cancel_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Start cancel flow from 24h reminder."""
    order_id = int(callback.data.split(":")[1])
    client_tg_id = callback.from_user.id

    # Get order data
    order = await get_order_for_confirmation(order_id, client_tg_id)

    if not order:
        await callback.answer("Заказ не найден")
        return

    if order["status"] not in ("new", "confirmed"):
        await callback.answer("Заказ уже обработан")
        return

    # Parse scheduled_at for display
    scheduled_at = datetime.fromisoformat(order["scheduled_at"])
    day = scheduled_at.day
    month = MONTHS_RU[scheduled_at.month]
    time_str = scheduled_at.strftime("%H:%M")

    # Store order data in state
    await state.update_data(
        cancel_order_id=order_id,
        cancel_scheduled_at=order["scheduled_at"],
        cancel_master_tg_id=order["master_tg_id"],
        cancel_master_name=order.get("master_name"),
        cancel_address=order.get("address"),
        cancel_services=order.get("services"),
    )

    text = (
        f"❌ Отмена записи\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📅 {day} {month}, {time_str}\n"
        f"📍 {order.get('address') or '—'}\n"
        f"🛠 {order.get('services') or '—'}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Укажите причину отмены:"
    )

    await callback.message.edit_text(text=text, reply_markup=client_cancel_reason_kb())
    await state.set_state(ClientCancelOrder.reason)
    await callback.answer()


@router.callback_query(ClientCancelOrder.reason, F.data.startswith("client_cancel:reason:"))
async def client_cancel_select_reason(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle cancel reason selection."""
    reason_code = callback.data.split(":")[2]

    reason_map = {
        "cant_come": "Не смогу прийти",
        "changed_mind": "Передумал(а)",
    }

    if reason_code == "custom":
        await callback.message.edit_text(
            text="✏️ Введите причину отмены:",
            reply_markup=None
        )
        await state.set_state(ClientCancelOrder.confirm)
        await state.update_data(cancel_waiting_custom_reason=True)
    else:
        reason = reason_map.get(reason_code, "Без причины")
        await state.update_data(cancel_reason=reason, cancel_waiting_custom_reason=False)

        data = await state.get_data()
        scheduled_at = datetime.fromisoformat(data.get("cancel_scheduled_at"))
        day = scheduled_at.day
        month = MONTHS_RU[scheduled_at.month]
        time_str = scheduled_at.strftime("%H:%M")

        text = (
            f"❌ Подтверждение отмены\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📅 {day} {month}, {time_str}\n"
            f"📍 {data.get('cancel_address') or '—'}\n"
            f"Причина: {reason}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Вы уверены?"
        )

        await callback.message.edit_text(text=text, reply_markup=client_cancel_confirm_kb())
        await state.set_state(ClientCancelOrder.confirm)

    await callback.answer()


@router.message(ClientCancelOrder.confirm)
async def client_cancel_custom_reason(message: Message, state: FSMContext) -> None:
    """Handle custom cancel reason input."""
    data = await state.get_data()

    if not data.get("cancel_waiting_custom_reason"):
        return

    reason = message.text.strip() if message.text else "Без причины"
    await state.update_data(cancel_reason=reason, cancel_waiting_custom_reason=False)

    scheduled_at = datetime.fromisoformat(data.get("cancel_scheduled_at"))
    day = scheduled_at.day
    month = MONTHS_RU[scheduled_at.month]
    time_str = scheduled_at.strftime("%H:%M")

    text = (
        f"❌ Подтверждение отмены\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📅 {day} {month}, {time_str}\n"
        f"📍 {data.get('cancel_address') or '—'}\n"
        f"Причина: {reason}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Вы уверены?"
    )

    await message.answer(text=text, reply_markup=client_cancel_confirm_kb())


@router.callback_query(ClientCancelOrder.confirm, F.data == "client_cancel:confirm:yes")
async def client_cancel_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Execute order cancel from client side."""
    global master_bot

    data = await state.get_data()
    order_id = data.get("cancel_order_id")
    reason = data.get("cancel_reason", "Клиент отменил")
    master_tg_id = data.get("cancel_master_tg_id")
    master_name = data.get("cancel_master_name")
    address = data.get("cancel_address")
    services = data.get("cancel_services")
    scheduled_at = datetime.fromisoformat(data.get("cancel_scheduled_at"))

    # Update order status
    await update_order_status(order_id, "cancelled", cancel_reason=reason)

    await state.clear()

    # Get client info
    tg_id = callback.from_user.id
    client = await get_client_by_tg_id(tg_id)

    # Show success to client
    text = (
        f"❌ Запись отменена.\n\n"
        f"Мастер {master_name} будет уведомлён.\n"
        f"Для новой записи свяжитесь с мастером."
    )

    await callback.message.edit_text(text=text, reply_markup=None)

    # Notify master
    if master_bot and master_tg_id:
        try:
            day = scheduled_at.day
            month = MONTHS_RU[scheduled_at.month]
            time_str = scheduled_at.strftime("%H:%M")

            master_text = (
                f"❌ Клиент отменил запись!\n\n"
                f"👤 {client.name if client else '—'}\n"
                f"📅 {day} {month}, {time_str}\n"
                f"📍 {address or '—'}\n"
                f"🛠 {services or '—'}\n"
                f"📝 Причина: {reason}"
            )
            await master_bot.send_message(chat_id=master_tg_id, text=master_text)
        except Exception as e:
            logger.error(f"Failed to notify master about cancellation: {e}")

    await callback.answer("Запись отменена")


@router.callback_query(F.data == "client_cancel:back")
async def client_cancel_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel the cancel flow."""
    await state.clear()
    await callback.message.edit_text(
        text="Отмена записи прервана.\n\nВаша запись осталась без изменений.",
        reply_markup=None
    )
    await callback.answer()


# =============================================================================
# Bot Setup
# =============================================================================

def setup_dispatcher() -> Dispatcher:
    """Create and configure dispatcher."""
    dp = Dispatcher(storage=MemoryStorage())
    # Outer middleware intercepts "Home" button before any filters/handlers
    dp.message.outer_middleware(HomeButtonMiddleware())
    dp.include_router(router)
    return dp


async def main() -> None:
    """Main entry point."""
    global master_bot
    from aiogram.types import BotCommand

    await init_db()
    logger.info("Database initialized")

    # Create bot instances
    bot = Bot(token=CLIENT_BOT_TOKEN)
    master_bot = Bot(token=MASTER_BOT_TOKEN)

    # Set bot commands for menu
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать"),
    ])
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="📱 Открыть",
            web_app=WebAppInfo(url=MINIAPP_URL)
        )
    )

    # Setup scheduler
    from src.scheduler import setup_scheduler, start_scheduler
    setup_scheduler(bot)
    start_scheduler()
    logger.info("Scheduler started")

    dp = setup_dispatcher()

    logger.info("Starting client bot...")
    try:
        await dp.start_polling(bot)
    finally:
        from src.scheduler import stop_scheduler
        stop_scheduler()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
