"""Client bot - for clients to view bonuses, history, and make requests."""

import logging
from datetime import date

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

from src.config import CLIENT_BOT_TOKEN, LOG_LEVEL
from src.states import ClientRegistration
from src.keyboards import (
    home_client_kb, client_bonuses_kb, client_bot_history_kb,
    client_promos_kb, client_master_info_kb, client_notifications_kb,
    skip_kb, share_contact_kb, stub_kb,
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
    save_client_home_message_id,
    toggle_client_notification,
    get_client_orders,
    get_client_bonus_log,
    get_active_campaigns,
)
from src.utils import format_phone, parse_date

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
    return (
        f"👋 Привет, {client.name}!\n\n"
        f"💰 Ваши бонусы: {master_client.bonus_balance} ₽\n"
        f"Мастер: {master.name}\n"
        f"━━━━━━━━━━━━━━━"
    )


async def show_home(bot: Bot, client, master, master_client, chat_id: int) -> int:
    """Show or update home screen. Returns message_id."""
    text = await build_home_text(client, master, master_client)
    keyboard = home_client_kb()

    if master_client.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=master_client.home_message_id,
                text=text,
                reply_markup=keyboard
            )
            return master_client.home_message_id
        except TelegramBadRequest:
            pass

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


async def get_client_context(tg_id: int) -> tuple:
    """Get client, master, and master_client for a user."""
    client = await get_client_by_tg_id(tg_id)
    if not client or not client.registered_via:
        return None, None, None

    master = await get_master_by_id(client.registered_via)
    if not master:
        return client, None, None

    master_client = await get_master_client(master.id, client.id)
    return client, master, master_client


# =============================================================================
# Start and Home Commands
# =============================================================================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /start command."""
    tg_id = message.from_user.id

    # Check if already registered
    client, master, master_client = await get_client_context(tg_id)
    if client and master and master_client:
        await state.clear()
        await show_home(bot, client, master, master_client, message.chat.id)
        return

    # Extract invite token
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Для регистрации нужна ссылка от вашего мастера.\n"
            "Попросите мастера отправить вам персональную ссылку."
        )
        return

    invite_token = args[1].strip()

    # Find master
    master = await get_master_by_invite_token(invite_token)
    if not master:
        await message.answer(
            "❌ Ссылка недействительна.\n\n"
            "Попросите мастера отправить вам актуальную ссылку."
        )
        return

    # Store master_id for registration
    await state.update_data(master_id=master.id)

    await message.answer(
        f"👋 Привет! Вы переходите к мастеру: {master.name}\n\n"
        "Давайте познакомимся.\n\n"
        "📝 Как вас зовут?"
    )
    await state.set_state(ClientRegistration.name)


@router.message(Command("home"))
async def cmd_home(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /home command."""
    tg_id = message.from_user.id

    client, master, master_client = await get_client_context(tg_id)
    if not client or not master or not master_client:
        await message.answer("Вы ещё не зарегистрированы. Перейдите по ссылке от мастера.")
        return

    await state.clear()
    await show_home(bot, client, master, master_client, message.chat.id)


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
    phone = format_phone(message.contact.phone_number)
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
async def reg_phone_text(message: Message, state: FSMContext) -> None:
    """Step 2: Save phone from text."""
    phone = format_phone(message.text.strip())
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

    # Link to master
    master_client = await link_client_to_master(master_id, client.id)
    master = await get_master_by_id(master_id)

    await state.clear()

    success_text = "✅ Регистрация завершена!\n\nДобро пожаловать!"

    if edit:
        await message.edit_text(success_text)
    else:
        await message.answer(success_text)

    await show_home(bot, client, master, master_client, message.chat.id)


# =============================================================================
# Navigation: Home
# =============================================================================

@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery, bot: Bot) -> None:
    """Return to home screen."""
    tg_id = callback.from_user.id

    client, master, master_client = await get_client_context(tg_id)
    if not client or not master or not master_client:
        await callback.answer("Ошибка")
        return

    text = await build_home_text(client, master, master_client)
    await edit_home_message(callback, text, home_client_kb())
    await callback.answer()


# =============================================================================
# Bonuses Section
# =============================================================================

@router.callback_query(F.data == "bonuses")
async def cb_bonuses(callback: CallbackQuery) -> None:
    """Show bonuses."""
    tg_id = callback.from_user.id

    client, master, master_client = await get_client_context(tg_id)
    if not client or not master:
        await callback.answer("Ошибка")
        return

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
        f"Баланс: {master_client.bonus_balance} ₽\n\n"
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

    client, master, master_client = await get_client_context(tg_id)
    if not client or not master:
        await callback.answer("Ошибка")
        return

    orders = await get_client_orders(master.id, client.id, limit=20)

    if orders:
        orders_text = "\n".join(
            f"• {o.get('scheduled_at', '')[:10] if o.get('scheduled_at') else '—'} — "
            f"{o.get('services', '—')[:25]} | {o.get('amount_total', 0)} ₽"
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

    client, master, master_client = await get_client_context(tg_id)
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
                except:
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

    client, master, master_client = await get_client_context(tg_id)
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

    client, master, master_client = await get_client_context(tg_id)
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

    await edit_home_message(callback, text, client_notifications_kb(
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

    client, master, master_client = await get_client_context(tg_id)
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

    await edit_home_message(callback, text, client_notifications_kb(
        master_client.notify_24h,
        master_client.notify_1h,
        master_client.notify_marketing,
        master_client.notify_promos,
    ))
    await callback.answer("Сохранено")


# =============================================================================
# FSM Stubs
# =============================================================================

@router.callback_query(F.data == "order_request")
async def cb_order_request(callback: CallbackQuery) -> None:
    """Order request stub."""
    text = "🚧 Заявка на заказ — в разработке"
    await edit_home_message(callback, text, stub_kb("home"))
    await callback.answer()


@router.callback_query(F.data == "question")
async def cb_question(callback: CallbackQuery) -> None:
    """Question stub."""
    text = "🚧 Вопрос мастеру — в разработке"
    await edit_home_message(callback, text, stub_kb("home"))
    await callback.answer()


@router.callback_query(F.data == "media")
async def cb_media(callback: CallbackQuery) -> None:
    """Media stub."""
    text = "🚧 Отправка фото/видео — в разработке"
    await edit_home_message(callback, text, stub_kb("home"))
    await callback.answer()


# =============================================================================
# Bot Setup
# =============================================================================

def setup_dispatcher() -> Dispatcher:
    """Create and configure dispatcher."""
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return dp


async def main() -> None:
    """Main entry point."""
    await init_db()
    logger.info("Database initialized")

    bot = Bot(token=CLIENT_BOT_TOKEN)
    dp = setup_dispatcher()

    logger.info("Starting client bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
