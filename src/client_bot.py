"""Client bot: inline navigation, client registration, and notification actions."""

import json
import logging
from datetime import date, datetime
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
    TelegramObject,
)

from src.config import CLIENT_BOT_TOKEN, LOG_LEVEL, MASTER_BOT_TOKEN
from src.database import (
    accrue_welcome_bonus,
    anonymize_client,
    confirm_order_by_client,
    create_client,
    get_active_campaigns,
    get_all_client_masters_by_tg_id,
    get_client_bonus_log,
    get_client_by_phone,
    get_client_by_tg_id,
    get_client_orders,
    get_master_by_id,
    get_master_by_invite_token,
    get_master_client,
    get_order_by_id_for_feedback,
    get_order_notification_context,
    init_db,
    link_client_to_master,
    link_existing_client_to_master,
    save_client_home_message_id,
    save_order_rating,
    toggle_client_notification,
    update_client,
    update_client_consent,
)
from src.keyboards import (
    back_kb,
    client_bonuses_kb,
    client_bot_history_kb,
    client_master_info_kb,
    client_notifications_back_kb,
    client_promos_kb,
    client_settings_kb,
    consent_kb,
    delete_confirm_kb,
    home_client_kb,
    home_reply_kb,
    share_contact_kb,
    skip_kb,
)
from src.notifications import contact_keyboard, order_action_keyboard
from src.states import ClientDeletion, ClientRegistration
from src.utils import (
    DEFAULT_FEEDBACK_REPLY_5,
    format_phone,
    get_currency_symbol,
    normalize_phone,
    parse_date,
    render_feedback_message,
)

master_bot: Bot | None = None
_active_masters: dict[int, int] = {}

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

router = Router()

MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


async def build_home_text(client, master, master_client) -> str:
    """Build client home screen text."""
    curr = get_currency_symbol(master.currency)
    return (
        f"👋 Привет, {client.name}!\n\n"
        f"💰 Ваши бонусы: {master_client.bonus_balance} {curr}\n"
        f"Мастер: {master.name}\n"
        "━━━━━━━━━━━━━━━"
    )


async def get_client_context(tg_id: int, master_id: int | None = None) -> tuple:
    """Return client, active master and link row for a Telegram user."""
    client = await get_client_by_tg_id(tg_id)
    if not client:
        return None, None, None

    masters = await get_all_client_masters_by_tg_id(tg_id)
    if not masters:
        return client, None, None

    if master_id is not None:
        entry = next((item for item in masters if item["master_id"] == master_id), None)
        if not entry:
            master_id = masters[0]["master_id"]
    else:
        master_id = masters[0]["master_id"]

    master = await get_master_by_id(master_id)
    if not master:
        return client, None, None

    master_client = await get_master_client(master.id, client.id)
    return client, master, master_client


async def ensure_home_reply_keyboard(bot: Bot, chat_id: int) -> None:
    """Set the persistent reply Home button with a silent service message."""
    try:
        msg = await bot.send_message(chat_id, "\u2060", reply_markup=home_reply_kb())
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except TelegramBadRequest:
            pass
    except TelegramBadRequest:
        pass


async def remove_reply_keyboard(bot: Bot, chat_id: int) -> None:
    """Silently remove a reply keyboard if Telegram still shows one."""
    try:
        msg = await bot.send_message(chat_id, "\u2060", reply_markup=ReplyKeyboardRemove())
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except TelegramBadRequest:
            pass
    except TelegramBadRequest:
        pass


async def show_home(bot: Bot, client, master, master_client, chat_id: int, force_new: bool = False) -> int:
    """Show or update the stored client home message."""
    text = await build_home_text(client, master, master_client)
    all_masters = await get_all_client_masters_by_tg_id(client.tg_id)
    keyboard = home_client_kb(multi_master=len(all_masters) > 1)

    if force_new and master_client.home_message_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=master_client.home_message_id)
        except TelegramBadRequest:
            pass

    if master_client.home_message_id and not force_new:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=master_client.home_message_id,
                text=text,
                reply_markup=keyboard,
            )
            return master_client.home_message_id
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc):
                return master_client.home_message_id

    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    await save_client_home_message_id(master.id, client.id, msg.message_id)
    return msg.message_id


async def edit_home_message(callback: CallbackQuery, text: str, keyboard) -> None:
    """Edit the current inline message and ignore no-op edits."""
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            logger.debug("Failed to edit client message: %s", exc)


async def show_master_select(bot: Bot, tg_id: int, chat_id: int) -> None:
    """Show master selector for multi-master clients."""
    masters = await get_all_client_masters_by_tg_id(tg_id)
    if not masters:
        await bot.send_message(chat_id, "Вы не привязаны ни к одному мастеру.")
        return

    rows = [
        [InlineKeyboardButton(
            text=f"{item['master_name']}" + (f" · {item['sphere']}" if item.get("sphere") else ""),
            callback_data=f"select_master:{item['master_id']}",
        )]
        for item in masters
    ]
    rows.append([InlineKeyboardButton(text="🏠 Главная", callback_data="home")])
    await bot.send_message(
        chat_id,
        "👥 У вас несколько мастеров. Выберите:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


class HomeButtonMiddleware(BaseMiddleware):
    """Intercept the persistent reply Home button before FSM handlers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text == "🏠 Домой":
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
                await event.answer("Вы не зарегистрированы. Перейдите по ссылке от специалиста.")
            return None

        return await handler(event, data)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /start and invite links."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    tg_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    invite_token = args[1].strip() if len(args) >= 2 else None
    if invite_token and invite_token.startswith("invite_"):
        invite_token = invite_token[7:]

    client = await get_client_by_tg_id(tg_id)

    if invite_token:
        master = await get_master_by_invite_token(invite_token)
        if not master:
            await bot.send_message(
                message.chat.id,
                "Ссылка недействительна.\n\n"
                "Попросите специалиста отправить вам актуальную ссылку.",
            )
            return

        if not client:
            await state.update_data(master_id=master.id)
            await bot.send_message(
                message.chat.id,
                "Привет!\n\n"
                "Для регистрации нам нужно ваше согласие на обработку персональных данных.\n\n"
                "Мы собираем: имя, телефон, дату рождения (опционально).\n"
                "Данные используются только для записи и бонусной программы.\n\n"
                '<a href="https://crmfit.ru/privacy">Политика конфиденциальности</a>',
                reply_markup=consent_kb(),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            await state.set_state(ClientRegistration.consent)
            return

        existing_link = await get_master_client(master.id, client.id)
        if not existing_link:
            await link_existing_client_to_master(client.id, master.id)
            await accrue_welcome_bonus(master.id, client.id)
            await bot.send_message(message.chat.id, f"Вы подключились к специалисту {master.name}!")
        else:
            await bot.send_message(message.chat.id, f"Вы уже подключены к специалисту {master.name}")

        _active_masters[tg_id] = master.id
        await state.clear()
        await ensure_home_reply_keyboard(bot, message.chat.id)
        master_client = await get_master_client(master.id, client.id)
        if master_client:
            await show_home(bot, client, master, master_client, message.chat.id, force_new=True)
        return

    if not client:
        await bot.send_message(
            message.chat.id,
            "Привет!\n\n"
            "Для регистрации нужна ссылка от вашего специалиста.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.clear()
    await ensure_home_reply_keyboard(bot, message.chat.id)
    client, master, master_client = await get_client_context(tg_id, _active_masters.get(tg_id))
    if client and master and master_client:
        _active_masters[tg_id] = master.id
        await show_home(bot, client, master, master_client, message.chat.id)
    else:
        await bot.send_message(message.chat.id, "Для начала работы нужна ссылка от специалиста.")


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /support command."""
    await state.clear()
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    client, master, master_client = await get_client_context(message.from_user.id, _active_masters.get(message.from_user.id))
    if not client or not master or not master_client:
        await bot.send_message(message.chat.id, "Вы не зарегистрированы. Перейдите по ссылке от специалиста.")
        return

    text = (
        "💬 Поддержка\n"
        "━━━━━━━━━━━━━━━\n"
        "По вопросам работы бота:\n\n"
        "Telegram: @pastushenko12\n"
        "E-mail: copypast.pe@gmail.com"
    )
    if master_client.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master_client.home_message_id,
                text=text,
                reply_markup=back_kb("client_settings"),
            )
            return
        except TelegramBadRequest:
            pass
    msg = await bot.send_message(message.chat.id, text, reply_markup=back_kb("client_settings"))
    await save_client_home_message_id(master.id, client.id, msg.message_id)


@router.message(Command("delete_me"))
async def cmd_delete_me(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /delete_me command."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    client, master, master_client = await get_client_context(message.from_user.id, _active_masters.get(message.from_user.id))
    if not client or not master or not master_client:
        await bot.send_message(message.chat.id, "Вы не зарегистрированы в системе.")
        return

    await state.set_state(ClientDeletion.confirm)
    await state.update_data(client_id=client.id)
    text = (
        "Удаление данных\n\n"
        "Будут удалены: имя, телефон, дата рождения и привязка к Telegram.\n"
        "История заказов сохранится анонимно.\n\n"
        "Это действие необратимо."
    )
    if master_client.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master_client.home_message_id,
                text=text,
                reply_markup=delete_confirm_kb(),
            )
            return
        except TelegramBadRequest:
            pass
    msg = await bot.send_message(message.chat.id, text, reply_markup=delete_confirm_kb())
    await save_client_home_message_id(master.id, client.id, msg.message_id)


@router.callback_query(F.data == "delete:confirm")
async def delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm data deletion."""
    client = await get_client_by_tg_id(callback.from_user.id)
    if client:
        await anonymize_client(client.id)
    await state.clear()
    await callback.message.edit_text("Ваши данные удалены.\n\nСпасибо, что были с нами!")
    await callback.answer()


@router.callback_query(F.data == "delete:cancel")
async def delete_cancel(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Cancel data deletion."""
    await state.clear()
    client, master, master_client = await get_client_context(callback.from_user.id, _active_masters.get(callback.from_user.id))
    if client and master and master_client:
        await show_home(bot, client, master, master_client, callback.message.chat.id)
    else:
        await callback.message.edit_text("Удаление отменено.")
    await callback.answer()


@router.callback_query(ClientRegistration.consent, F.data == "consent:agree")
async def consent_agree(callback: CallbackQuery, state: FSMContext) -> None:
    """User agreed to privacy policy."""
    await state.update_data(consent_given_at=datetime.now().isoformat())
    await callback.message.edit_text("Спасибо за согласие!\n\nКак вас зовут?")
    await state.set_state(ClientRegistration.name)
    await callback.answer()


@router.callback_query(ClientRegistration.consent, F.data == "consent:decline")
async def consent_decline(callback: CallbackQuery, state: FSMContext) -> None:
    """User declined privacy policy."""
    await state.clear()
    await callback.message.edit_text(
        "Вы отказались от обработки данных.\n\n"
        "Без согласия регистрация невозможна. Если передумаете, перейдите по ссылке от специалиста снова."
    )
    await callback.answer()


@router.message(ClientRegistration.name)
async def reg_name(message: Message, state: FSMContext) -> None:
    """Save client name."""
    name = message.text.strip()[:100]
    await state.update_data(name=name)
    await message.answer(
        f"Приятно познакомиться, {name}!\n\n"
        "Поделитесь номером телефона. Это нужно для связи со специалистом.",
        reply_markup=share_contact_kb(),
    )
    await state.set_state(ClientRegistration.phone)


@router.message(ClientRegistration.phone, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext) -> None:
    """Save client phone from contact."""
    phone = normalize_phone(message.contact.phone_number) or format_phone(message.contact.phone_number)
    await state.update_data(phone=phone)
    await message.answer(
        "Когда у вас день рождения?\n"
        "(в формате ДД.ММ или ДД.ММ.ГГГГ)",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("Или пропустите этот шаг:", reply_markup=skip_kb())
    await state.set_state(ClientRegistration.birthday)


@router.message(ClientRegistration.phone)
async def reg_phone_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save client phone from text."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    phone = normalize_phone(message.text.strip())
    if not phone:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Неверный формат номера. Введите с кодом страны: +7..., +995..., +380...",
        )
        return

    await state.update_data(phone=phone)
    await message.answer(
        "Когда у вас день рождения?\n"
        "(в формате ДД.ММ или ДД.ММ.ГГГГ)",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("Или пропустите этот шаг:", reply_markup=skip_kb())
    await state.set_state(ClientRegistration.birthday)


@router.message(ClientRegistration.birthday)
async def reg_birthday(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save birthday and complete registration."""
    birthday = parse_date(message.text)
    await state.update_data(birthday=birthday.isoformat() if birthday else None)
    await complete_registration(message, state, bot)


@router.callback_query(ClientRegistration.birthday, F.data == "skip")
async def reg_birthday_skip(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Skip birthday and complete registration."""
    await state.update_data(birthday=None)
    await complete_registration(callback.message, state, bot, edit=True)
    await callback.answer()


async def complete_registration(message: Message, state: FSMContext, bot: Bot, edit: bool = False) -> None:
    """Complete client registration and show inline home."""
    data = await state.get_data()
    tg_id = message.chat.id
    master_id = data["master_id"]

    phone = data.get("phone")
    existing_client = await get_client_by_phone(phone) if phone else None
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

    if data.get("consent_given_at"):
        await update_client_consent(client.id, data["consent_given_at"])

    master_client = await link_client_to_master(master_id, client.id)
    master = await get_master_by_id(master_id)
    await accrue_welcome_bonus(master_id, client.id)
    await state.clear()
    _active_masters[tg_id] = master_id

    success_text = "Регистрация завершена!"
    if edit:
        await message.edit_text(success_text)
    else:
        await message.answer(success_text, reply_markup=ReplyKeyboardRemove())
    await ensure_home_reply_keyboard(bot, message.chat.id)

    if master:
        await bot.send_message(message.chat.id, f"Вы подключились к специалисту {master.name}.")
        await show_home(bot, client, master, master_client, message.chat.id, force_new=True)


@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    """Return to client home."""
    await state.clear()
    client, master, master_client = await get_client_context(callback.from_user.id, _active_masters.get(callback.from_user.id))
    if not client or not master or not master_client:
        await callback.answer("Ошибка")
        return

    text = await build_home_text(client, master, master_client)
    all_masters = await get_all_client_masters_by_tg_id(client.tg_id)
    await edit_home_message(callback, text, home_client_kb(multi_master=len(all_masters) > 1))
    await callback.answer()


@router.callback_query(F.data.startswith("select_master:"))
async def cb_select_master(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    """Select active master for this client."""
    await state.clear()
    try:
        master_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка при выборе мастера")
        return

    _active_masters[callback.from_user.id] = master_id
    client, master, master_client = await get_client_context(callback.from_user.id, master_id)
    if not client or not master or not master_client:
        await callback.answer("Ошибка при выборе мастера")
        return

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await show_home(bot, client, master, master_client, callback.message.chat.id, force_new=True)
    await callback.answer()


@router.callback_query(F.data == "change_master")
async def cb_change_master(callback: CallbackQuery, bot: Bot) -> None:
    """Show master selector."""
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await show_master_select(bot, callback.from_user.id, callback.message.chat.id)
    await callback.answer()


@router.callback_query(F.data == "bonuses")
async def cb_bonuses(callback: CallbackQuery) -> None:
    """Show bonus balance and recent operations."""
    client, master, master_client = await get_client_context(callback.from_user.id, _active_masters.get(callback.from_user.id))
    if not client or not master or not master_client:
        await callback.answer("Ошибка")
        return

    curr = get_currency_symbol(master.currency)
    bonus_log = await get_client_bonus_log(master.id, client.id, limit=10)
    if bonus_log:
        rows = [
            f"• {item.get('created_at', '')[:10] if item.get('created_at') else '—'} "
            f"{'+' if item.get('amount', 0) > 0 else ''}{item.get('amount', 0)} — "
            f"{item.get('comment') or 'Операция'}"
            for item in bonus_log
        ]
        log_text = "\n".join(rows)
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


@router.callback_query(F.data == "history")
async def cb_history(callback: CallbackQuery) -> None:
    """Show completed order history."""
    client, master, _master_client = await get_client_context(callback.from_user.id, _active_masters.get(callback.from_user.id))
    if not client or not master:
        await callback.answer("Ошибка")
        return

    curr = get_currency_symbol(master.currency)
    orders = await get_client_orders(master.id, client.id, limit=20)
    done_orders = [order for order in orders if order.get("status") == "done"]
    if done_orders:
        rows = [
            f"• {order.get('scheduled_at', '')[:10] if order.get('scheduled_at') else '—'} — "
            f"{order.get('services') or '—'} | {order.get('amount_total') or 0} {curr}"
            for order in done_orders
        ]
        orders_text = "\n".join(rows)
    else:
        orders_text = "Выполненных заказов пока нет"

    text = (
        "📋 История визитов\n"
        "━━━━━━━━━━━━━━━\n"
        f"{orders_text}\n"
        "━━━━━━━━━━━━━━━"
    )
    await edit_home_message(callback, text, client_bot_history_kb())
    await callback.answer()


@router.callback_query(F.data == "promos")
async def cb_promos(callback: CallbackQuery) -> None:
    """Show active campaigns."""
    _client, master, _master_client = await get_client_context(callback.from_user.id, _active_masters.get(callback.from_user.id))
    if not master:
        await callback.answer("Ошибка")
        return

    campaigns = await get_active_campaigns(master.id)
    if campaigns:
        parts = []
        for campaign in campaigns:
            until_text = ""
            if campaign.active_to:
                try:
                    d = date.fromisoformat(str(campaign.active_to))
                    until_text = f"До {d.day} {MONTHS_RU[d.month]}"
                except Exception:
                    until_text = ""
            item = f"🔥 {campaign.title or 'Акция'}\n{campaign.text}"
            if until_text:
                item += f"\n{until_text}"
            parts.append(item)
        promos_text = "\n\n".join(parts)
    else:
        promos_text = "Акций пока нет. Следите за обновлениями!"

    text = (
        "🎁 Акции\n"
        "━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        "━━━━━━━━━━━━━━━"
    )
    await edit_home_message(callback, text, client_promos_kb())
    await callback.answer()


@router.callback_query(F.data == "master_info")
async def cb_master_info(callback: CallbackQuery) -> None:
    """Show current master contact info."""
    _client, master, _master_client = await get_client_context(callback.from_user.id, _active_masters.get(callback.from_user.id))
    if not master:
        await callback.answer("Ошибка")
        return

    phone_link = normalize_phone(master.phone or "") or normalize_phone(master.contacts or "")
    phone = master.phone or master.contacts or "—"
    socials = master.telegram or master.socials or "—"
    text = (
        "👨‍🔧 Ваш мастер\n"
        "━━━━━━━━━━━━━━━\n"
        f"{master.name}\n"
        f"{master.sphere or ''}\n\n"
        f"📞 {phone}\n"
        f"🌐 {socials}\n"
        f"🕐 {master.work_hours or '—'}\n"
        "━━━━━━━━━━━━━━━"
    )
    await edit_home_message(
        callback,
        text,
        client_master_info_kb(
            phone=phone_link or master.phone,
            telegram=master.telegram,
            master_tg_id=master.tg_id,
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "master_call")
async def cb_master_call(callback: CallbackQuery) -> None:
    """Send current master's contact card for calling."""
    _client, master, _master_client = await get_client_context(callback.from_user.id, _active_masters.get(callback.from_user.id))
    if not master:
        await callback.answer("Ошибка", show_alert=True)
        return

    phone = normalize_phone(master.phone or "") or normalize_phone(master.contacts or "")
    if not phone:
        await callback.answer("Телефон мастера не указан", show_alert=True)
        return

    if callback.message:
        await callback.message.answer_contact(
            phone_number=phone,
            first_name=master.name or "Мастер",
        )
    await callback.answer("Контакт отправлен")


@router.callback_query(F.data == "client_settings")
async def cb_client_settings(callback: CallbackQuery) -> None:
    """Show client settings menu."""
    text = (
        "⚙️ Настройки\n"
        "━━━━━━━━━━━━━━━"
    )
    await edit_home_message(callback, text, client_settings_kb())
    await callback.answer()


@router.callback_query(F.data == "notifications")
async def cb_notifications(callback: CallbackQuery) -> None:
    """Show client notification settings."""
    _client, _master, master_client = await get_client_context(callback.from_user.id, _active_masters.get(callback.from_user.id))
    if not master_client:
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
    """Toggle a client notification setting."""
    client, master, master_client = await get_client_context(callback.from_user.id, _active_masters.get(callback.from_user.id))
    if not client or not master or not master_client:
        await callback.answer("Ошибка")
        return

    field = callback.data.split(":")[2]
    try:
        new_value = await toggle_client_notification(master.id, client.id, field)
    except ValueError:
        await callback.answer("Ошибка")
        return
    setattr(master_client, field, new_value)

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


@router.callback_query(F.data == "client_support")
async def cb_client_support(callback: CallbackQuery) -> None:
    """Show support contacts."""
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
    """Ask for profile deletion confirmation from settings."""
    client, _master, _master_client = await get_client_context(callback.from_user.id, _active_masters.get(callback.from_user.id))
    if not client:
        await callback.answer("Ошибка")
        return

    await state.set_state(ClientDeletion.confirm)
    await state.update_data(client_id=client.id)
    text = (
        "Удаление данных\n"
        "━━━━━━━━━━━━━━━\n"
        "Будут удалены: имя, телефон, дата рождения и привязка к Telegram.\n"
        "История заказов сохранится анонимно.\n\n"
        "Это действие необратимо."
    )
    await edit_home_message(callback, text, delete_confirm_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("feedback:"))
async def handle_feedback_rating(callback: CallbackQuery) -> None:
    """Handle client rating response from post-order feedback."""
    global master_bot

    try:
        _, order_id_raw, rating_raw = (callback.data or "").split(":")
        order_id = int(order_id_raw)
        rating = int(rating_raw)
    except (ValueError, AttributeError):
        await callback.answer()
        return

    if rating < 1 or rating > 5:
        await callback.answer()
        return

    await save_order_rating(order_id, rating)
    try:
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    order = await get_order_by_id_for_feedback(order_id)

    if rating == 5:
        reply_text = render_feedback_message(
            template=order.get("feedback_reply_5") if order else None,
            default=DEFAULT_FEEDBACK_REPLY_5,
            master_name=order.get("master_name") if order else "",
            services=order.get("services") if order else "",
        )
        reply_markup = None
        raw_buttons = order.get("review_buttons") if order else None
        if raw_buttons:
            try:
                parsed_buttons = json.loads(raw_buttons)
                rows = []
                for button in parsed_buttons[:3]:
                    label = (button or {}).get("label")
                    url = (button or {}).get("url")
                    if label and url:
                        rows.append([InlineKeyboardButton(text=str(label), url=str(url))])
                if rows:
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=rows)
            except Exception:
                logger.warning("Invalid review_buttons JSON for order %s", order_id)

        if callback.message:
            await callback.message.answer(reply_text, reply_markup=reply_markup)
    elif rating == 4:
        if callback.message:
            await callback.message.answer("Расскажите, что можно улучшить? Это поможет стать лучше.")

        if order and order.get("master_tg_id") and master_bot:
            client_name = order.get("client_name") or "Клиент"
            try:
                await master_bot.send_message(
                    order["master_tg_id"],
                    f"ℹ️ {client_name} оценил визит на 4.\nЗаказ #{order_id}",
                )
            except Exception as exc:
                logger.warning("Failed to notify master for rating 4, order %s: %s", order_id, exc)
    else:
        if callback.message:
            await callback.message.answer("Мы свяжемся с вами в ближайшее время.")

        if order and order.get("master_tg_id") and master_bot:
            client_name = order.get("client_name") or "Клиент"
            try:
                await master_bot.send_message(
                    order["master_tg_id"],
                    f"⚠️ {client_name} недоволен!\n"
                    f"Оценка: {rating} из 5\n"
                    f"Заказ #{order_id}\n\n"
                    "Свяжитесь с клиентом.",
                )
            except Exception as exc:
                logger.warning("Failed to alert master for rating %s, order %s: %s", rating, order_id, exc)

    await callback.answer("Спасибо за оценку!")


@router.callback_query(F.data.startswith("confirm_order:"))
async def handle_order_confirmation(callback: CallbackQuery) -> None:
    """Handle order confirmation from 24h reminder."""
    global master_bot

    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    order = await get_order_notification_context(order_id, client_tg_id=callback.from_user.id)
    if not order:
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    if order.get("client_confirmed"):
        await callback.answer("Запись уже подтверждена", show_alert=True)
        return

    if order.get("status") not in ("new", "confirmed"):
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    await confirm_order_by_client(order_id, order["client_id"])

    scheduled_at = datetime.fromisoformat(order["scheduled_at"])
    date_str = f"{scheduled_at.day} {MONTHS_RU[scheduled_at.month]}"
    time_str = scheduled_at.strftime("%H:%M")
    services = order.get("services") or "—"
    master_name = order.get("master_name") or "специалист"
    address = (order.get("address") or "").strip()

    new_text = (
        "Вы подтвердили запись:\n\n"
        f"{services}\n"
        f"{date_str}, {time_str} — {master_name}"
    )
    if address:
        new_text += f"\n{address}"
    new_text += "\n\nЖдём вас!"

    if callback.message:
        await callback.message.edit_text(
            text=new_text,
            reply_markup=order_action_keyboard(order_id, master_id=order.get("master_id")),
        )

    if master_bot and order.get("master_tg_id"):
        master_text = (
            "Клиент подтвердил запись:\n\n"
            f"{order.get('client_name') or 'Клиент'}\n"
            f"{services}\n"
            f"{date_str}, {time_str}"
        )
        await master_bot.send_message(chat_id=order["master_tg_id"], text=master_text)

    await callback.answer("Запись подтверждена")


@router.callback_query(F.data.startswith("contact_order:"))
async def handle_contact_order(callback: CallbackQuery) -> None:
    """Show specialist contacts for an order notification."""
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    order = await get_order_notification_context(order_id, client_tg_id=callback.from_user.id)
    if not order:
        await callback.answer("Запись больше не активна", show_alert=True)
        return

    phone = (order.get("master_phone") or "").strip()
    telegram = (order.get("master_telegram") or "").strip()
    contacts = (order.get("master_contacts") or "").strip()

    lines = [order.get("master_name") or "Специалист", ""]
    lines.append(f"Телефон: {phone or '—'}")
    lines.append(f"Telegram: {telegram or '—'}")
    if contacts and contacts not in {phone, telegram}:
        lines.extend(["", contacts])

    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=contact_keyboard(
                phone=phone,
                telegram=telegram,
                master_id=order.get("master_id"),
            ),
        )
    await callback.answer()


def setup_dispatcher() -> Dispatcher:
    """Create and configure dispatcher."""
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.outer_middleware(HomeButtonMiddleware())
    dp.include_router(router)
    return dp


async def main() -> None:
    """Main entry point."""
    global master_bot
    from aiogram.types import BotCommand

    await init_db()
    logger.info("Database initialized")

    bot = Bot(token=CLIENT_BOT_TOKEN)
    master_bot = Bot(token=MASTER_BOT_TOKEN)

    await bot.set_my_commands([
        BotCommand(command="start", description="Начать"),
        BotCommand(command="support", description="Поддержка"),
        BotCommand(command="delete_me", description="Удалить мои данные"),
    ])

    from src.scheduler import setup_scheduler, start_scheduler
    setup_scheduler(bot, master_bot=master_bot)
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
