"""Master bot - for service providers to manage clients, orders, and marketing."""

import logging
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery, TelegramObject, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from typing import Callable, Dict, Any, Awaitable
import asyncio

from src.config import MASTER_BOT_TOKEN, CLIENT_BOT_USERNAME, LOG_LEVEL
from src.states import (
    MasterRegistration, CreateOrder, CreateClientInOrder,
    CompleteOrder, MoveOrder, CancelOrder,
    ClientAdd, ServiceAdd, ServiceEdit,
    ProfileEdit, BonusSettingsEdit, BonusMessageEdit, ClientEdit, ClientNote, BonusManual,
    BroadcastFSM, PromoFSM, ReportPeriodFSM,
)
from src.keyboards import (
    home_master_kb, orders_kb, order_card_kb, calendar_kb,
    clients_kb, clients_paginated_kb, client_card_kb, client_history_kb, client_bonus_kb,
    marketing_kb, reports_kb, settings_kb, settings_profile_kb,
    settings_bonus_kb, settings_services_kb, settings_invite_kb, bonus_message_kb, timezone_kb,
    skip_kb, stub_kb, home_reply_kb,
    # Order keyboards
    client_search_results_kb, order_address_kb, order_calendar_kb,
    order_hour_kb, order_minutes_kb, order_services_kb, order_confirm_kb,
    order_edit_field_kb, complete_amount_kb, payment_type_kb, bonus_use_kb,
    complete_confirm_kb, move_confirm_kb, move_hour_kb, move_minutes_kb,
    cancel_reason_kb, cancel_confirm_kb,
    # Service keyboards
    service_edit_kb, service_archived_kb,
    # Client keyboards
    client_edit_kb,
    # Marketing keyboards
    broadcast_cancel_kb, broadcast_media_kb, broadcast_segment_kb,
    broadcast_confirm_kb, broadcast_no_recipients_kb,
    promo_cancel_kb, promo_date_from_kb, promo_confirm_kb,
    promo_card_kb, promo_end_confirm_kb,
    # Report keyboards
    report_period_cancel_kb,
    # Google Calendar keyboards
    gc_not_connected_kb, gc_connected_kb, gc_disconnect_confirm_kb,
)
from src.database import (
    init_db,
    get_master_by_tg_id,
    get_master_by_id,
    create_master,
    update_master,
    update_client,
    save_master_home_message_id,
    get_orders_today,
    get_orders_by_date,
    get_order_by_id,
    get_active_dates,
    search_clients,
    get_client_with_stats,
    get_client_by_id,
    get_client_orders,
    get_client_bonus_log,
    get_services,
    get_reports,
    # Order functions
    create_client,
    link_client_to_master,
    get_master_client,
    update_master_client,
    create_order,
    create_order_items,
    update_order_status,
    update_order_schedule,
    get_last_client_address,
    apply_bonus_transaction,
    save_gc_event_id,
    # Service functions
    get_archived_services,
    get_service_by_id,
    create_service,
    update_service,
    archive_service,
    restore_service,
    # Client functions
    update_client_note,
    manual_bonus_transaction,
    get_client_orders_history,
    # Marketing functions
    get_broadcast_recipients,
    get_broadcast_recipients_count,
    save_campaign,
    get_active_promos,
    get_promo_by_id,
    deactivate_promo,
    get_marketing_recipients_count,
    # Confirmation functions
    mark_order_confirmed_by_client,
    reset_order_for_reconfirmation,
    # Clients pagination
    get_clients_paginated,
    # Bonus settings
    update_master_bonus_setting,
)
from src.utils import (
    generate_invite_token, normalize_phone, get_timezone_display,
    render_bonus_message, DEFAULT_WELCOME_MESSAGE, DEFAULT_BIRTHDAY_MESSAGE,
)
from src import notifications
from src import google_calendar

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize router
router = Router()


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

            master = await get_master_by_tg_id(tg_id)
            if master:
                await state.clear()
                try:
                    await event.delete()
                except TelegramBadRequest:
                    pass
                await show_home(bot, master, event.chat.id, force_new=True)
            else:
                # Not registered - show message
                await event.answer("Вы не зарегистрированы. Отправьте /start")
            return  # Always stop propagation for "Home" button

        return await handler(event, data)


MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]

MONTHS_RU_NOM = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]


# =============================================================================
# Home Screen
# =============================================================================

async def build_home_text(master) -> str:
    """Build home screen text."""
    today = date.today()
    day = today.day
    month = MONTHS_RU[today.month]

    orders = await get_orders_today(master.id)

    if orders:
        def get_time(scheduled_at: str) -> str:
            """Extract HH:MM from ISO datetime string."""
            return scheduled_at[11:16] if len(scheduled_at) >= 16 else "—"

        orders_text = "\n".join(
            f"• {get_time(o.get('scheduled_at', ''))} — "
            f"{o.get('client_name', 'Клиент')} | {o.get('address', 'адрес не указан')[:30]}"
            for o in orders
        )
    else:
        orders_text = "• Заказов на сегодня нет"

    return (
        f"👋 Привет, {master.name}!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📅 Сегодня, {day} {month}:\n\n"
        f"{orders_text}\n"
        f"━━━━━━━━━━━━━━━"
    )


async def show_home(bot: Bot, master, chat_id: int, force_new: bool = False) -> int:
    """Show or update home screen. Returns message_id.

    Args:
        force_new: If True, always send new message (delete old if exists)
    """
    text = await build_home_text(master)
    keyboard = home_master_kb()

    # Delete old message if force_new
    if force_new and master.home_message_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=master.home_message_id)
        except TelegramBadRequest:
            pass
        # Send new message
        msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
        await save_master_home_message_id(master.id, msg.message_id)
        return msg.message_id

    # Try to edit existing message
    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=keyboard
            )
            return master.home_message_id
        except TelegramBadRequest as e:
            # "message is not modified" - no need to send new message
            if "message is not modified" in str(e):
                return master.home_message_id
            # Otherwise message was deleted or not found - send new

    # Send new message
    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    await save_master_home_message_id(master.id, msg.message_id)
    return msg.message_id


async def edit_home_message(callback: CallbackQuery, text: str, keyboard) -> None:
    """Edit the home message with new content."""
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass


# =============================================================================
# Start and Home Commands
# =============================================================================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /start command."""
    tg_id = message.from_user.id

    master = await get_master_by_tg_id(tg_id)
    if master:
        await state.clear()
        await state.update_data(current_screen="home")
        # Show home menu (force_new to show at bottom of chat)
        await show_home(bot, master, message.chat.id, force_new=True)
        return

    # Start registration
    await message.answer(
        "👋 Добро пожаловать в Master CRM Bot!\n\n"
        "Давайте настроим ваш профиль.\n\n"
        "📝 Введите ваше имя или псевдоним:",
        reply_markup=home_reply_kb()
    )
    await state.set_state(MasterRegistration.name)


@router.message(Command("home"))
async def cmd_home(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle /home command."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    if not master:
        await message.answer("Вы ещё не зарегистрированы. Отправьте /start")
        return

    await state.clear()
    await state.update_data(current_screen="home")
    await show_home(bot, master, message.chat.id)


# =============================================================================
# Registration FSM
# =============================================================================

@router.message(MasterRegistration.name)
async def reg_name(message: Message, state: FSMContext) -> None:
    """Step 1: Save name."""
    name = message.text.strip()[:100]
    await state.update_data(name=name)

    await message.answer(
        f"Отлично, {name}!\n\n"
        "🔧 Укажите вашу сферу деятельности:\n"
        "(например: клининг, сантехника, электрика, маникюр)",
        reply_markup=skip_kb()
    )
    await state.set_state(MasterRegistration.sphere)


@router.message(MasterRegistration.sphere)
async def reg_sphere(message: Message, state: FSMContext) -> None:
    """Step 2: Save sphere."""
    sphere = message.text.strip()[:200]
    await state.update_data(sphere=sphere)

    await message.answer(
        "🕐 Выберите ваш часовой пояс:\n"
        "(для отправки поздравлений клиентам)",
        reply_markup=timezone_kb(back_to=None)
    )
    await state.set_state(MasterRegistration.timezone)


@router.callback_query(MasterRegistration.sphere, F.data == "skip")
async def reg_sphere_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 2: Skip sphere."""
    await state.update_data(sphere=None)
    await callback.message.edit_text(
        "🕐 Выберите ваш часовой пояс:\n"
        "(для отправки поздравлений клиентам)"
    )
    await callback.message.answer("Выберите:", reply_markup=timezone_kb(back_to=None))
    await state.set_state(MasterRegistration.timezone)
    await callback.answer()


@router.callback_query(MasterRegistration.timezone, F.data.startswith("set_timezone:"))
async def reg_timezone(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Save timezone."""
    tz_code = callback.data.split(":")[1]
    await state.update_data(timezone=tz_code)

    tz_display = get_timezone_display(tz_code)
    await callback.message.edit_text(f"✅ Часовой пояс: {tz_display}")

    await callback.message.answer(
        "📞 Введите контакты для клиентов:\n"
        "(телефон, мессенджеры, email)",
        reply_markup=skip_kb()
    )
    await state.set_state(MasterRegistration.contacts)
    await callback.answer()


@router.message(MasterRegistration.contacts)
async def reg_contacts(message: Message, state: FSMContext) -> None:
    """Step 4: Save contacts."""
    contacts = message.text.strip()[:500]
    await state.update_data(contacts=contacts)

    await message.answer(
        "🔗 Укажите ссылки на соцсети и каналы:\n"
        "(Instagram, Telegram-канал, VK и т.д.)",
        reply_markup=skip_kb()
    )
    await state.set_state(MasterRegistration.socials)


@router.callback_query(MasterRegistration.contacts, F.data == "skip")
async def reg_contacts_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Skip contacts."""
    await state.update_data(contacts=None)
    await callback.message.edit_text(
        "🔗 Укажите ссылки на соцсети и каналы:\n"
        "(Instagram, Telegram-канал, VK и т.д.)"
    )
    await callback.message.answer("Или пропустите:", reply_markup=skip_kb())
    await state.set_state(MasterRegistration.socials)
    await callback.answer()


@router.message(MasterRegistration.socials)
async def reg_socials(message: Message, state: FSMContext) -> None:
    """Step 4: Save socials."""
    socials = message.text.strip()[:500]
    await state.update_data(socials=socials)

    await message.answer(
        "🕐 Укажите режим работы:\n"
        "(например: пн-пт 9:00-19:00, сб 10:00-16:00)",
        reply_markup=skip_kb()
    )
    await state.set_state(MasterRegistration.work_hours)


@router.callback_query(MasterRegistration.socials, F.data == "skip")
async def reg_socials_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 4: Skip socials."""
    await state.update_data(socials=None)
    await callback.message.edit_text(
        "🕐 Укажите режим работы:\n"
        "(например: пн-пт 9:00-19:00, сб 10:00-16:00)"
    )
    await callback.message.answer("Или пропустите:", reply_markup=skip_kb())
    await state.set_state(MasterRegistration.work_hours)
    await callback.answer()


@router.message(MasterRegistration.work_hours)
async def reg_work_hours(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 5: Save work hours and complete."""
    work_hours = message.text.strip()[:200]
    await state.update_data(work_hours=work_hours)
    await complete_registration(message, state, bot)


@router.callback_query(MasterRegistration.work_hours, F.data == "skip")
async def reg_work_hours_skip(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Step 5: Skip work hours."""
    await state.update_data(work_hours=None)
    await complete_registration(callback.message, state, bot, edit=True)
    await callback.answer()


async def complete_registration(message: Message, state: FSMContext, bot: Bot, edit: bool = False) -> None:
    """Complete master registration."""
    data = await state.get_data()
    tg_id = message.chat.id

    invite_token = generate_invite_token()

    master = await create_master(
        tg_id=tg_id,
        name=data["name"],
        invite_token=invite_token,
        sphere=data.get("sphere"),
        contacts=data.get("contacts"),
        socials=data.get("socials"),
        work_hours=data.get("work_hours"),
        timezone=data.get("timezone", "Europe/Moscow"),
    )

    await state.clear()
    await state.update_data(current_screen="home")

    success_text = (
        "✅ Регистрация завершена!\n\n"
        f"Ваша ссылка для приглашения клиентов:\n"
        f"t.me/{CLIENT_BOT_USERNAME}?start={invite_token}\n\n"
        "Отправьте её клиентам, чтобы они могли зарегистрироваться."
    )

    if edit:
        await message.edit_text(success_text)
    else:
        await message.answer(success_text)

    # Send reply keyboard
    await bot.send_message(message.chat.id, "🏠", reply_markup=home_reply_kb())
    await show_home(bot, master, message.chat.id)


# =============================================================================
# Navigation: Home
# =============================================================================

@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Return to home screen."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    if not master:
        await callback.answer("Ошибка")
        return

    await state.update_data(current_screen="home")
    text = await build_home_text(master)
    await edit_home_message(callback, text, home_master_kb())
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    """Do nothing callback for non-interactive buttons."""
    await callback.answer()


# =============================================================================
# Orders Section
# =============================================================================

@router.callback_query(F.data == "orders")
async def cb_orders(callback: CallbackQuery, state: FSMContext) -> None:
    """Show orders for today."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    if not master:
        await callback.answer("Ошибка")
        return

    await state.update_data(current_screen="orders", orders_date=date.today().isoformat())

    today = date.today()
    orders = await get_orders_today(master.id, all_statuses=True)

    day = today.day
    month = MONTHS_RU[today.month]

    text = (
        f"📦 Заказы — Сегодня, {day} {month}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, orders_kb(orders, today))
    await callback.answer()


@router.callback_query(F.data.startswith("orders:view:"))
async def cb_order_view(callback: CallbackQuery, state: FSMContext) -> None:
    """View order card."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    order_id = int(callback.data.split(":")[2])
    order = await get_order_by_id(order_id, master.id)

    if not order:
        await callback.answer("Заказ не найден")
        return

    scheduled = order.get("scheduled_at", "")
    if scheduled:
        dt = datetime.fromisoformat(scheduled)
        time_str = dt.strftime("%H:%M")
        date_str = f"{dt.day} {MONTHS_RU[dt.month]}"
    else:
        time_str = "—"
        date_str = "—"

    status_map = {
        "new": "новый",
        "confirmed": "подтверждён",
        "done": "выполнен",
        "cancelled": "отменён",
        "moved": "перенесён",
    }

    status = order.get("status", "")
    status_emoji = {
        "new": "🆕",
        "confirmed": "📌",
        "done": "✅",
        "cancelled": "❌",
        "moved": "📅",
    }

    text = (
        f"📋 Заказ #{order['id']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {order.get('client_name', '—')}\n"
        f"📞 {order.get('client_phone', '—')}\n"
        f"📍 {order.get('address', '—')}\n"
        f"🕐 {time_str} | {date_str}\n"
        f"🛠 {order.get('services', '—')}\n"
        f"💰 Итого: {order.get('amount_total', 0) or '—'} ₽\n"
        f"📊 Статус: {status_emoji.get(status, '')} {status_map.get(status, status)}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, order_card_kb(order_id, status, order.get("client_id")))
    await callback.answer()


@router.callback_query(F.data == "orders:calendar")
async def cb_orders_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    """Show calendar."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    today = date.today()
    active_dates = await get_active_dates(master.id, today.year, today.month)

    text = "📅 Выберите дату:"

    await edit_home_message(callback, text, calendar_kb(today.year, today.month, active_dates))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^orders:calendar:\d+:\d+$"))
async def cb_orders_calendar_nav(callback: CallbackQuery, state: FSMContext) -> None:
    """Navigate calendar months."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    parts = callback.data.split(":")
    year = int(parts[2])
    month = int(parts[3])

    active_dates = await get_active_dates(master.id, year, month)

    text = "📅 Выберите дату:"

    await edit_home_message(callback, text, calendar_kb(year, month, active_dates))
    await callback.answer()


@router.callback_query(F.data.startswith("orders:calendar:date:"))
async def cb_orders_calendar_date(callback: CallbackQuery, state: FSMContext) -> None:
    """Select date from calendar."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    date_str = callback.data.split(":")[3]
    selected_date = date.fromisoformat(date_str)

    orders = await get_orders_by_date(master.id, selected_date, all_statuses=True)

    day = selected_date.day
    month = MONTHS_RU[selected_date.month]

    text = (
        f"📦 Заказы — {day} {month}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await state.update_data(orders_date=date_str)
    await edit_home_message(callback, text, orders_kb(orders, selected_date))
    await callback.answer()


# =============================================================================
# Create Order FSM (7 steps)
# =============================================================================

@router.callback_query(F.data == "orders:new")
async def cb_orders_new(callback: CallbackQuery, state: FSMContext) -> None:
    """Start creating new order - Step 1: Search client."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    if not master:
        await callback.answer("Ошибка")
        return

    await state.update_data(
        order_master_id=master.id,
        order_client_id=None,
        order_client_name=None,
        order_address=None,
        order_date=None,
        order_hour=None,
        order_minutes=None,
        order_services=[],
        order_custom_services=[],
        order_amount=None,
    )

    text = (
        "📋 Новый заказ — Шаг 1/7\n"
        "━━━━━━━━━━━━━━━\n"
        "🔍 Введите имя или телефон клиента:"
    )

    await edit_home_message(callback, text, client_search_results_kb([]))
    await state.set_state(CreateOrder.search_client)
    await callback.answer()


@router.message(CreateOrder.search_client)
async def order_search_client(message: Message, state: FSMContext, bot: Bot) -> None:
    """Search for client by name/phone."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    if not master:
        return

    query = message.text.strip()
    results = await search_clients(master.id, query)

    try:
        await message.delete()
    except:
        pass

    if results:
        text = (
            "📋 Новый заказ — Шаг 1/7\n"
            "━━━━━━━━━━━━━━━\n"
            f"🔍 Результаты: «{query}»\n"
            "Выберите клиента:"
        )
    else:
        text = (
            "📋 Новый заказ — Шаг 1/7\n"
            "━━━━━━━━━━━━━━━\n"
            f"Клиент «{query}» не найден.\n"
            "Попробуйте ещё или создайте нового:"
        )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=client_search_results_kb(results)
            )
        except TelegramBadRequest:
            pass


@router.callback_query(CreateOrder.search_client, F.data.startswith("order:client:"))
async def order_select_client(callback: CallbackQuery, state: FSMContext) -> None:
    """Select client or create new one."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    if callback.data == "order:client:new":
        # Start mini-FSM for new client creation
        text = (
            "👤 Новый клиент\n"
            "━━━━━━━━━━━━━━━\n"
            "Введите имя клиента:"
        )
        await edit_home_message(callback, text, stub_kb("order:cancel"))
        await state.set_state(CreateClientInOrder.name)
        await callback.answer()
        return

    # Selected existing client
    client_id = int(callback.data.split(":")[2])
    client = await get_client_by_id(client_id)

    if not client:
        await callback.answer("Клиент не найден")
        return

    await state.update_data(order_client_id=client_id, order_client_name=client.name)

    # Step 2: Address
    last_address = await get_last_client_address(master.id, client_id)
    await state.update_data(order_last_address=last_address)

    if last_address:
        text = (
            "📋 Новый заказ — Шаг 2/7\n"
            "━━━━━━━━━━━━━━━\n"
            f"👤 Клиент: {client.name}\n"
            "━━━━━━━━━━━━━━━\n"
            "📍 Выберите адрес или введите новый:"
        )
    else:
        text = (
            "📋 Новый заказ — Шаг 2/7\n"
            "━━━━━━━━━━━━━━━\n"
            f"👤 Клиент: {client.name}\n"
            "━━━━━━━━━━━━━━━\n"
            "📍 Введите адрес:"
        )

    await edit_home_message(callback, text, order_address_kb(last_address))
    await state.set_state(CreateOrder.address)
    await callback.answer()


# Mini-FSM for creating client during order creation
@router.message(CreateClientInOrder.name)
async def order_new_client_name(message: Message, state: FSMContext, bot: Bot) -> None:
    """New client name."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    name = message.text.strip()[:100]
    await state.update_data(new_client_name=name)

    try:
        await message.delete()
    except:
        pass

    text = (
        "👤 Новый клиент\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {name}\n"
        "━━━━━━━━━━━━━━━\n"
        "📞 Введите телефон:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=stub_kb("order:cancel")
            )
        except TelegramBadRequest:
            pass

    await state.set_state(CreateClientInOrder.phone)


@router.message(CreateClientInOrder.phone)
async def order_new_client_phone(message: Message, state: FSMContext, bot: Bot) -> None:
    """New client phone."""
    import asyncio

    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        await message.delete()
    except:
        pass

    # Validate and normalize phone
    phone = normalize_phone(message.text.strip())
    if not phone:
        # Show error briefly, then delete
        error_msg = await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Неверный формат номера. Введите с кодом страны: +7..., +995..., +380..."
        )
        await asyncio.sleep(2)
        try:
            await error_msg.delete()
        except:
            pass
        return

    await state.update_data(new_client_phone=phone)

    data = await state.get_data()
    name = data.get("new_client_name")

    text = (
        "👤 Новый клиент\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        "━━━━━━━━━━━━━━━\n"
        "🎂 Введите дату рождения (ДД.ММ.ГГГГ) или пропустите:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=skip_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(CreateClientInOrder.birthday)


@router.message(CreateClientInOrder.birthday)
async def order_new_client_birthday(message: Message, state: FSMContext, bot: Bot) -> None:
    """New client birthday."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    birthday_text = message.text.strip()
    birthday = None

    # Try to parse birthday
    try:
        from src.utils import parse_date
        birthday = parse_date(birthday_text)
    except:
        pass

    try:
        await message.delete()
    except:
        pass

    await finish_new_client_creation(state, master, bot, message.chat.id, birthday)


@router.callback_query(CreateClientInOrder.birthday, F.data == "skip")
async def order_new_client_birthday_skip(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Skip birthday for new client."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    await finish_new_client_creation(state, master, bot, callback.message.chat.id, None)
    await callback.answer()


async def finish_new_client_creation(state: FSMContext, master, bot: Bot, chat_id: int, birthday: str) -> None:
    """Finish creating new client and continue order flow."""
    data = await state.get_data()
    name = data.get("new_client_name")
    phone = data.get("new_client_phone")

    # Create client
    client = await create_client(
        name=name,
        phone=phone,
        birthday=birthday,
        registered_via=master.id
    )

    # Link to master
    await link_client_to_master(master.id, client.id)

    await state.update_data(order_client_id=client.id, order_client_name=name)

    # Continue to Step 2: Address
    text = (
        "📋 Новый заказ — Шаг 2/7\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 Клиент: {name} ✅ создан\n"
        "━━━━━━━━━━━━━━━\n"
        "📍 Введите адрес:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=order_address_kb(None)
            )
        except TelegramBadRequest:
            pass

    await state.set_state(CreateOrder.address)


@router.callback_query(CreateOrder.address, F.data == "order:address:last")
async def order_use_last_address(callback: CallbackQuery, state: FSMContext) -> None:
    """Use last address for client."""
    data = await state.get_data()
    last_address = data.get("order_last_address")

    if not last_address:
        await callback.answer("Адрес не найден")
        return

    await callback.answer()  # Answer immediately to prevent double-click issues
    await state.update_data(order_address=last_address)
    await go_to_date_step(callback, state)


@router.message(CreateOrder.address)
async def order_enter_address(message: Message, state: FSMContext, bot: Bot) -> None:
    """Enter address manually."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    address = message.text.strip()[:500]
    await state.update_data(order_address=address)

    try:
        await message.delete()
    except:
        pass

    # Create a fake callback-like context for go_to_date_step
    data = await state.get_data()
    client_name = data.get("order_client_name")
    today = date.today()

    text = (
        "📋 Новый заказ — Шаг 3/7\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {client_name}\n"
        f"📍 {address}\n"
        "━━━━━━━━━━━━━━━\n"
        "📅 Выберите дату:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=order_calendar_kb(today.year, today.month)
            )
        except TelegramBadRequest:
            pass

    await state.set_state(CreateOrder.date)


async def go_to_date_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Go to date selection step."""
    data = await state.get_data()
    client_name = data.get("order_client_name")
    address = data.get("order_address")
    today = date.today()

    text = (
        "📋 Новый заказ — Шаг 3/7\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {client_name}\n"
        f"📍 {address}\n"
        "━━━━━━━━━━━━━━━\n"
        "📅 Выберите дату:"
    )

    await edit_home_message(callback, text, order_calendar_kb(today.year, today.month))
    await state.set_state(CreateOrder.date)


@router.callback_query(CreateOrder.date, F.data.regexp(r"^order:cal:\d+:\d+$"))
async def order_calendar_nav(callback: CallbackQuery, state: FSMContext) -> None:
    """Navigate calendar."""
    data = await state.get_data()
    client_name = data.get("order_client_name")
    address = data.get("order_address")

    parts = callback.data.split(":")
    year = int(parts[2])
    month = int(parts[3])

    text = (
        "📋 Новый заказ — Шаг 3/7\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {client_name}\n"
        f"📍 {address}\n"
        "━━━━━━━━━━━━━━━\n"
        "📅 Выберите дату:"
    )

    await edit_home_message(callback, text, order_calendar_kb(year, month))
    await callback.answer()


@router.callback_query(CreateOrder.date, F.data.startswith("order:date:"))
async def order_select_date(callback: CallbackQuery, state: FSMContext) -> None:
    """Select date for order."""
    date_str = callback.data.split(":")[2]
    selected_date = date.fromisoformat(date_str)

    await state.update_data(order_date=date_str)

    data = await state.get_data()
    client_name = data.get("order_client_name")
    address = data.get("order_address")

    day = selected_date.day
    month = MONTHS_RU[selected_date.month]

    text = (
        "📋 Новый заказ — Шаг 4/7\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {client_name}\n"
        f"📍 {address}\n"
        f"📅 {day} {month}\n"
        "━━━━━━━━━━━━━━━\n"
        "⏰ Выберите час:"
    )

    await edit_home_message(callback, text, order_hour_kb())
    await state.set_state(CreateOrder.hour)
    await callback.answer()


@router.callback_query(CreateOrder.hour, F.data.startswith("order:hour:"))
async def order_select_hour(callback: CallbackQuery, state: FSMContext) -> None:
    """Select hour for order."""
    hour = int(callback.data.split(":")[2])
    await state.update_data(order_hour=hour)

    data = await state.get_data()
    client_name = data.get("order_client_name")
    address = data.get("order_address")
    date_str = data.get("order_date")
    selected_date = date.fromisoformat(date_str)

    day = selected_date.day
    month = MONTHS_RU[selected_date.month]

    text = (
        "📋 Новый заказ — Шаг 4/7\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {client_name}\n"
        f"📍 {address}\n"
        f"📅 {day} {month}\n"
        "━━━━━━━━━━━━━━━\n"
        "⏰ Выберите минуты:"
    )

    await edit_home_message(callback, text, order_minutes_kb(hour))
    await state.set_state(CreateOrder.minutes)
    await callback.answer()


@router.callback_query(CreateOrder.minutes, F.data.startswith("order:minutes:"))
async def order_select_minutes(callback: CallbackQuery, state: FSMContext) -> None:
    """Select minutes for order."""
    minutes = int(callback.data.split(":")[2])
    await state.update_data(order_minutes=minutes)

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    # Go to services selection
    services = await get_services(master.id)
    services_list = [{"id": s.id, "name": s.name, "price": s.price} for s in services]

    data = await state.get_data()
    client_name = data.get("order_client_name")
    address = data.get("order_address")
    date_str = data.get("order_date")
    selected_date = date.fromisoformat(date_str)
    hour = data.get("order_hour")

    day = selected_date.day
    month = MONTHS_RU[selected_date.month]
    time_str = f"{hour}:{minutes:02d}"

    await state.update_data(available_services=services_list)

    text = (
        "📋 Новый заказ — Шаг 5/7\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {client_name}\n"
        f"📍 {address}\n"
        f"📅 {day} {month} в {time_str}\n"
        "━━━━━━━━━━━━━━━\n"
        "🛠 Выберите услуги:"
    )

    await edit_home_message(callback, text, order_services_kb(services_list, [], []))
    await state.set_state(CreateOrder.services)
    await callback.answer()


@router.callback_query(CreateOrder.services, F.data.startswith("order:service:"))
async def order_select_service(callback: CallbackQuery, state: FSMContext) -> None:
    """Select or toggle a service."""
    service_data = callback.data.split(":")[2]

    if service_data == "custom":
        # Enter custom service
        data = await state.get_data()
        client_name = data.get("order_client_name")

        text = (
            "📋 Новый заказ — Шаг 5/7\n"
            "━━━━━━━━━━━━━━━\n"
            f"👤 {client_name}\n"
            "━━━━━━━━━━━━━━━\n"
            "✏️ Введите название услуги:"
        )

        await edit_home_message(callback, text, stub_kb("order:services:back"))
        await state.set_state(CreateOrder.custom_service)
        await callback.answer()
        return

    service_id = int(service_data)
    data = await state.get_data()
    selected = data.get("order_services", [])

    # Toggle service
    if service_id in selected:
        selected.remove(service_id)
    else:
        selected.append(service_id)

    await state.update_data(order_services=selected)

    # Update display
    client_name = data.get("order_client_name")
    address = data.get("order_address")
    date_str = data.get("order_date")
    selected_date = date.fromisoformat(date_str)
    hour = data.get("order_hour")
    minutes = data.get("order_minutes")
    services_list = data.get("available_services", [])
    custom_services = data.get("order_custom_services", [])

    day = selected_date.day
    month = MONTHS_RU[selected_date.month]
    time_str = f"{hour}:{minutes:02d}"

    # Build selected services text
    selected_names = [s["name"] for s in services_list if s["id"] in selected]
    selected_names.extend(custom_services)
    services_text = ", ".join(selected_names) if selected_names else "не выбраны"

    text = (
        "📋 Новый заказ — Шаг 5/7\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {client_name}\n"
        f"📍 {address}\n"
        f"📅 {day} {month} в {time_str}\n"
        f"🛠 {services_text}\n"
        "━━━━━━━━━━━━━━━\n"
        "Выберите услуги:"
    )

    await edit_home_message(callback, text, order_services_kb(services_list, selected, custom_services))
    await callback.answer()


@router.message(CreateOrder.custom_service)
async def order_enter_custom_service(message: Message, state: FSMContext, bot: Bot) -> None:
    """Enter custom service name."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    custom_name = message.text.strip()[:200]

    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    custom_services = data.get("order_custom_services", [])
    custom_services.append(custom_name)
    await state.update_data(order_custom_services=custom_services)

    # Return to services selection
    client_name = data.get("order_client_name")
    address = data.get("order_address")
    date_str = data.get("order_date")
    selected_date = date.fromisoformat(date_str)
    hour = data.get("order_hour")
    minutes = data.get("order_minutes")
    selected = data.get("order_services", [])
    services_list = data.get("available_services", [])

    day = selected_date.day
    month = MONTHS_RU[selected_date.month]
    time_str = f"{hour}:{minutes:02d}"

    selected_names = [s["name"] for s in services_list if s["id"] in selected]
    selected_names.extend(custom_services)
    services_text = ", ".join(selected_names)

    text = (
        "📋 Новый заказ — Шаг 5/7\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {client_name}\n"
        f"📍 {address}\n"
        f"📅 {day} {month} в {time_str}\n"
        f"🛠 {services_text}\n"
        "━━━━━━━━━━━━━━━\n"
        "Выберите услуги:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=order_services_kb(services_list, selected, custom_services)
            )
        except TelegramBadRequest:
            pass

    await state.set_state(CreateOrder.services)


@router.callback_query(CreateOrder.services, F.data == "order:services:done")
async def order_services_done(callback: CallbackQuery, state: FSMContext) -> None:
    """Finish services selection, go to amount."""
    data = await state.get_data()
    selected = data.get("order_services", [])
    custom_services = data.get("order_custom_services", [])

    if not selected and not custom_services:
        await callback.answer("Выберите хотя бы одну услугу")
        return

    client_name = data.get("order_client_name")
    address = data.get("order_address")
    date_str = data.get("order_date")
    selected_date = date.fromisoformat(date_str)
    hour = data.get("order_hour")
    minutes = data.get("order_minutes")
    services_list = data.get("available_services", [])

    day = selected_date.day
    month = MONTHS_RU[selected_date.month]
    time_str = f"{hour}:{minutes:02d}"

    selected_names = [s["name"] for s in services_list if s["id"] in selected]
    selected_names.extend(custom_services)
    services_text = ", ".join(selected_names)

    # Calculate suggested amount from services
    suggested_amount = sum(s["price"] for s in services_list if s["id"] in selected and s["price"])

    text = (
        "📋 Новый заказ — Шаг 6/7\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {client_name}\n"
        f"📍 {address}\n"
        f"📅 {day} {month} в {time_str}\n"
        f"🛠 {services_text}\n"
        "━━━━━━━━━━━━━━━\n"
        f"💰 Введите сумму{' (предлагаем ' + str(suggested_amount) + ' ₽)' if suggested_amount else ''}:"
    )

    await edit_home_message(callback, text, stub_kb("order:cancel"))
    await state.set_state(CreateOrder.amount)
    await callback.answer()


@router.message(CreateOrder.amount)
async def order_enter_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    """Enter order amount."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("Введите положительное целое число")
        return

    try:
        await message.delete()
    except:
        pass

    await state.update_data(order_amount=amount)

    # Show confirmation screen
    data = await state.get_data()
    client_name = data.get("order_client_name")
    address = data.get("order_address")
    date_str = data.get("order_date")
    selected_date = date.fromisoformat(date_str)
    hour = data.get("order_hour")
    minutes = data.get("order_minutes")
    selected = data.get("order_services", [])
    custom_services = data.get("order_custom_services", [])
    services_list = data.get("available_services", [])

    day = selected_date.day
    month = MONTHS_RU[selected_date.month]
    time_str = f"{hour}:{minutes:02d}"

    selected_names = [s["name"] for s in services_list if s["id"] in selected]
    selected_names.extend(custom_services)
    services_text = ", ".join(selected_names)

    text = (
        "📋 Новый заказ — Подтверждение\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 Клиент: {client_name}\n"
        f"📍 Адрес: {address}\n"
        f"📅 Дата: {day} {month} в {time_str}\n"
        f"🛠 Услуги: {services_text}\n"
        f"💰 Сумма: {amount} ₽\n"
        "━━━━━━━━━━━━━━━\n"
        "Всё верно?"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=order_confirm_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(CreateOrder.confirm)


@router.callback_query(CreateOrder.confirm, F.data == "order:confirm:yes")
async def order_confirm_create(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Create the order."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    client_id = data.get("order_client_id")
    address = data.get("order_address")
    date_str = data.get("order_date")
    hour = data.get("order_hour")
    minutes = data.get("order_minutes")
    amount = data.get("order_amount")
    selected = data.get("order_services", [])
    custom_services = data.get("order_custom_services", [])
    services_list = data.get("available_services", [])

    # Create datetime
    scheduled_at = datetime.fromisoformat(f"{date_str}T{hour:02d}:{minutes:02d}:00")

    # Create order
    order_id = await create_order(
        master_id=master.id,
        client_id=client_id,
        address=address,
        scheduled_at=scheduled_at,
        amount_total=amount
    )

    # Create order items
    order_items = []
    for s in services_list:
        if s["id"] in selected:
            order_items.append({"name": s["name"], "price": s["price"] or 0})
    for custom_name in custom_services:
        order_items.append({"name": custom_name, "price": 0})

    await create_order_items(order_id, order_items)

    # Google Calendar integration
    client = await get_client_by_id(client_id)
    services_text = ", ".join(item["name"] for item in order_items)

    try:
        gc_event_id = await google_calendar.create_event(
            master_id=master.id,
            client_name=client.name,
            client_phone=client.phone or "",
            services=services_text,
            address=address,
            amount=amount,
            scheduled_at=scheduled_at
        )

        if gc_event_id:
            await save_gc_event_id(order_id, gc_event_id)
    except Exception as e:
        logger.error(f"GC create_event error: {e}")

    # Send notification to client
    if client.tg_id:
        await notifications.notify_order_created(
            client=client,
            order={
                "id": order_id,
                "scheduled_at": scheduled_at,
                "address": address,
                "amount_total": amount
            },
            master=master,
            services=order_items
        )

    # Clear FSM and show orders screen
    await state.clear()
    await state.update_data(current_screen="orders", orders_date=date.today().isoformat())

    today = date.today()
    orders = await get_orders_today(master.id, all_statuses=True)

    day = today.day
    month = MONTHS_RU[today.month]

    text = (
        f"✅ Заказ создан!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 Заказы — Сегодня, {day} {month}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, orders_kb(orders, today))
    await callback.answer("Заказ создан!")


@router.callback_query(CreateOrder.confirm, F.data == "order:edit")
async def order_edit_fields(callback: CallbackQuery, state: FSMContext) -> None:
    """Show edit field selection."""
    text = (
        "✏️ Что изменить?\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, order_edit_field_kb())
    await state.set_state(CreateOrder.edit_field)
    await callback.answer()


@router.callback_query(CreateOrder.edit_field, F.data == "order:back_to_confirm")
async def order_back_to_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to confirmation screen."""
    data = await state.get_data()
    client_name = data.get("order_client_name")
    address = data.get("order_address")
    date_str = data.get("order_date")
    selected_date = date.fromisoformat(date_str)
    hour = data.get("order_hour")
    minutes = data.get("order_minutes")
    amount = data.get("order_amount")
    selected = data.get("order_services", [])
    custom_services = data.get("order_custom_services", [])
    services_list = data.get("available_services", [])

    day = selected_date.day
    month = MONTHS_RU[selected_date.month]
    time_str = f"{hour}:{minutes:02d}"

    selected_names = [s["name"] for s in services_list if s["id"] in selected]
    selected_names.extend(custom_services)
    services_text = ", ".join(selected_names)

    text = (
        "📋 Новый заказ — Подтверждение\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 Клиент: {client_name}\n"
        f"📍 Адрес: {address}\n"
        f"📅 Дата: {day} {month} в {time_str}\n"
        f"🛠 Услуги: {services_text}\n"
        f"💰 Сумма: {amount} ₽\n"
        "━━━━━━━━━━━━━━━\n"
        "Всё верно?"
    )

    await edit_home_message(callback, text, order_confirm_kb())
    await state.set_state(CreateOrder.confirm)
    await callback.answer()


@router.callback_query(CreateOrder.edit_field, F.data.startswith("order:edit:"))
async def order_edit_specific_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to edit a specific field."""
    field = callback.data.split(":")[2]

    if field == "client":
        text = (
            "📋 Изменить клиента\n"
            "━━━━━━━━━━━━━━━\n"
            "🔍 Введите имя или телефон клиента:"
        )
        await edit_home_message(callback, text, client_search_results_kb([]))
        await state.set_state(CreateOrder.search_client)
    elif field == "address":
        data = await state.get_data()
        last_address = data.get("order_last_address")
        text = (
            "📋 Изменить адрес\n"
            "━━━━━━━━━━━━━━━\n"
            "📍 Введите новый адрес:"
        )
        await edit_home_message(callback, text, order_address_kb(last_address))
        await state.set_state(CreateOrder.address)
    elif field == "date":
        today = date.today()
        text = (
            "📋 Изменить дату\n"
            "━━━━━━━━━━━━━━━\n"
            "📅 Выберите дату:"
        )
        await edit_home_message(callback, text, order_calendar_kb(today.year, today.month))
        await state.set_state(CreateOrder.date)
    elif field == "time":
        text = (
            "📋 Изменить время\n"
            "━━━━━━━━━━━━━━━\n"
            "⏰ Выберите час:"
        )
        await edit_home_message(callback, text, order_hour_kb())
        await state.set_state(CreateOrder.hour)
    elif field == "services":
        tg_id = callback.from_user.id
        master = await get_master_by_tg_id(tg_id)
        services = await get_services(master.id)
        services_list = [{"id": s.id, "name": s.name, "price": s.price} for s in services]
        data = await state.get_data()
        selected = data.get("order_services", [])
        custom_services = data.get("order_custom_services", [])

        text = (
            "📋 Изменить услуги\n"
            "━━━━━━━━━━━━━━━\n"
            "🛠 Выберите услуги:"
        )
        await state.update_data(available_services=services_list)
        await edit_home_message(callback, text, order_services_kb(services_list, selected, custom_services))
        await state.set_state(CreateOrder.services)
    elif field == "amount":
        text = (
            "📋 Изменить сумму\n"
            "━━━━━━━━━━━━━━━\n"
            "💰 Введите новую сумму:"
        )
        await edit_home_message(callback, text, stub_kb("order:back_to_confirm"))
        await state.set_state(CreateOrder.amount)

    await callback.answer()


# Cancel order creation
@router.callback_query(F.data == "order:cancel")
async def order_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel order creation - return to orders screen."""
    await state.clear()

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    await state.update_data(current_screen="orders", orders_date=date.today().isoformat())

    today = date.today()
    orders = await get_orders_today(master.id, all_statuses=True)

    day = today.day
    month = MONTHS_RU[today.month]

    text = (
        f"📦 Заказы — Сегодня, {day} {month}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, orders_kb(orders, today))
    await callback.answer("Отменено")


# =============================================================================
# Complete Order FSM
# =============================================================================

@router.callback_query(F.data.startswith("orders:complete:"))
async def cb_orders_complete(callback: CallbackQuery, state: FSMContext) -> None:
    """Start completing an order."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    order_id = int(callback.data.split(":")[2])
    order = await get_order_by_id(order_id, master.id)

    if not order:
        await callback.answer("Заказ не найден")
        return

    await state.update_data(
        complete_order_id=order_id,
        complete_amount=order.get("amount_total", 0),
        complete_payment_type=None,
        complete_bonus_spent=0
    )

    amount = order.get("amount_total", 0)

    text = (
        "✅ Провести заказ\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {order.get('client_name', '—')}\n"
        f"🛠 {order.get('services', '—')}\n"
        "━━━━━━━━━━━━━━━\n"
        f"💰 Сумма: {amount} ₽\n"
        "Подтвердите или измените:"
    )

    await edit_home_message(callback, text, complete_amount_kb(amount))
    await state.set_state(CompleteOrder.confirm_amount)
    await callback.answer()


@router.callback_query(CompleteOrder.confirm_amount, F.data == "complete:amount:confirm")
async def complete_amount_confirmed(callback: CallbackQuery, state: FSMContext) -> None:
    """Amount confirmed, go to payment type."""
    text = (
        "✅ Провести заказ\n"
        "━━━━━━━━━━━━━━━\n"
        "💳 Выберите способ оплаты:"
    )

    await edit_home_message(callback, text, payment_type_kb())
    await state.set_state(CompleteOrder.payment_type)
    await callback.answer()


@router.callback_query(CompleteOrder.confirm_amount, F.data == "complete:amount:change")
async def complete_amount_change(callback: CallbackQuery, state: FSMContext) -> None:
    """Change amount."""
    text = (
        "✅ Провести заказ\n"
        "━━━━━━━━━━━━━━━\n"
        "💰 Введите новую сумму:"
    )

    await edit_home_message(callback, text, stub_kb("complete:cancel"))
    await callback.answer()


@router.message(CompleteOrder.confirm_amount)
async def complete_enter_new_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    """Enter new amount."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("Введите положительное целое число")
        return

    try:
        await message.delete()
    except:
        pass

    await state.update_data(complete_amount=amount)

    text = (
        "✅ Провести заказ\n"
        "━━━━━━━━━━━━━━━\n"
        "💳 Выберите способ оплаты:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=payment_type_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(CompleteOrder.payment_type)


@router.callback_query(CompleteOrder.payment_type, F.data.startswith("complete:pay:"))
async def complete_select_payment(callback: CallbackQuery, state: FSMContext) -> None:
    """Select payment type."""
    payment_type = callback.data.split(":")[2]
    await state.update_data(complete_payment_type=payment_type)

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    order_id = data.get("complete_order_id")
    order = await get_order_by_id(order_id, master.id)
    amount = data.get("complete_amount")

    # Check if bonus can be used
    if master.bonus_enabled:
        mc = await get_master_client(master.id, order.get("client_id"))
        if mc and mc.bonus_balance > 0:
            # Calculate max bonus that can be used
            max_percent = master.bonus_max_spend
            max_by_percent = int(amount * max_percent / 100)
            max_can_use = min(mc.bonus_balance, max_by_percent)

            if max_can_use > 0:
                text = (
                    "✅ Провести заказ\n"
                    "━━━━━━━━━━━━━━━\n"
                    f"💰 Сумма: {amount} ₽\n"
                    "━━━━━━━━━━━━━━━\n"
                    "🎁 Списать бонусы?"
                )

                await edit_home_message(callback, text, bonus_use_kb(mc.bonus_balance, max_can_use))
                await state.update_data(complete_max_bonus=max_can_use)
                await state.set_state(CompleteOrder.use_bonus)
                await callback.answer()
                return

    # No bonus - go to confirmation
    await go_to_complete_confirm(callback, state)
    await callback.answer()


@router.callback_query(CompleteOrder.use_bonus, F.data == "complete:bonus:yes")
async def complete_use_bonus(callback: CallbackQuery, state: FSMContext) -> None:
    """Use bonus points."""
    data = await state.get_data()
    max_bonus = data.get("complete_max_bonus", 0)

    text = (
        "✅ Провести заказ\n"
        "━━━━━━━━━━━━━━━\n"
        f"🎁 Введите сумму бонусов (макс. {max_bonus} ₽):"
    )

    await edit_home_message(callback, text, stub_kb("complete:cancel"))
    await state.set_state(CompleteOrder.bonus_amount)
    await callback.answer()


@router.callback_query(CompleteOrder.use_bonus, F.data == "complete:bonus:no")
async def complete_no_bonus(callback: CallbackQuery, state: FSMContext) -> None:
    """Don't use bonus."""
    await state.update_data(complete_bonus_spent=0)
    await go_to_complete_confirm(callback, state)
    await callback.answer()


@router.message(CompleteOrder.bonus_amount)
async def complete_enter_bonus_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    """Enter bonus amount to use."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    max_bonus = data.get("complete_max_bonus", 0)

    try:
        bonus = int(message.text.strip())
        if bonus <= 0 or bonus > max_bonus:
            raise ValueError()
    except ValueError:
        await message.answer(f"Введите число от 1 до {max_bonus}")
        return

    try:
        await message.delete()
    except:
        pass

    await state.update_data(complete_bonus_spent=bonus)

    # Go to confirmation
    amount = data.get("complete_amount")
    payment_type = data.get("complete_payment_type")

    payment_names = {
        "cash": "Наличные",
        "card": "Карта",
        "transfer": "Перевод",
        "invoice": "По счёту"
    }

    final_amount = amount - bonus
    bonus_accrued = round(final_amount * master.bonus_rate / 100) if master.bonus_enabled else 0

    text = (
        "✅ Провести заказ — Подтверждение\n"
        "━━━━━━━━━━━━━━━\n"
        f"💰 Сумма: {amount} ₽\n"
        f"🎁 Списано бонусов: {bonus} ₽\n"
        f"💵 К оплате: {final_amount} ₽\n"
        f"💳 Оплата: {payment_names.get(payment_type, payment_type)}\n"
        f"⭐ Будет начислено: +{bonus_accrued} ₽\n"
        "━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=complete_confirm_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(CompleteOrder.confirm)


async def go_to_complete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Go to completion confirmation."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    amount = data.get("complete_amount")
    payment_type = data.get("complete_payment_type")
    bonus_spent = data.get("complete_bonus_spent", 0)

    payment_names = {
        "cash": "Наличные",
        "card": "Карта",
        "transfer": "Перевод",
        "invoice": "По счёту"
    }

    final_amount = amount - bonus_spent
    bonus_accrued = round(final_amount * master.bonus_rate / 100) if master.bonus_enabled else 0

    text = (
        "✅ Провести заказ — Подтверждение\n"
        "━━━━━━━━━━━━━━━\n"
        f"💰 Сумма: {amount} ₽\n"
    )

    if bonus_spent > 0:
        text += f"🎁 Списано бонусов: {bonus_spent} ₽\n"
        text += f"💵 К оплате: {final_amount} ₽\n"

    text += f"💳 Оплата: {payment_names.get(payment_type, payment_type)}\n"

    if master.bonus_enabled:
        text += f"⭐ Будет начислено: +{bonus_accrued} ₽\n"

    text += "━━━━━━━━━━━━━━━"

    await edit_home_message(callback, text, complete_confirm_kb())
    await state.set_state(CompleteOrder.confirm)


@router.callback_query(CompleteOrder.confirm, F.data == "complete:confirm:yes")
async def complete_order_final(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Complete the order."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    order_id = data.get("complete_order_id")
    amount = data.get("complete_amount")
    payment_type = data.get("complete_payment_type")
    bonus_spent = data.get("complete_bonus_spent", 0)

    final_amount = amount - bonus_spent
    bonus_accrued = round(final_amount * master.bonus_rate / 100) if master.bonus_enabled else 0

    # Get order details
    order = await get_order_by_id(order_id, master.id)
    client_id = order.get("client_id")

    # Update order status
    await update_order_status(
        order_id,
        "done",
        amount_total=amount,
        bonus_spent=bonus_spent,
        payment_type=payment_type,
        done_at=datetime.now().isoformat()
    )

    # Apply bonus transaction
    new_balance = 0
    if bonus_spent > 0 or bonus_accrued > 0:
        new_balance, _ = await apply_bonus_transaction(
            master.id, client_id, order_id, bonus_spent, bonus_accrued
        )
    else:
        mc = await get_master_client(master.id, client_id)
        new_balance = mc.bonus_balance if mc else 0

    # Delete GC event if exists
    if order.get("gc_event_id"):
        try:
            await google_calendar.delete_event(master.id, order.get("gc_event_id"))
        except Exception as e:
            logger.error(f"GC delete_event error: {e}")

    # Notify client
    client = await get_client_by_id(client_id)
    if client and client.tg_id:
        await notifications.notify_order_done(
            client=client,
            order={
                "services": order.get("services", ""),
                "amount_total": amount,
                "bonus_spent": bonus_spent
            },
            master=master,
            bonus_accrued=bonus_accrued,
            new_balance=new_balance
        )

    await state.clear()

    # Show updated order card
    updated_order = await get_order_by_id(order_id, master.id)
    scheduled = updated_order.get("scheduled_at", "")
    if scheduled:
        dt = datetime.fromisoformat(scheduled)
        time_str = dt.strftime("%H:%M")
        date_str = f"{dt.day} {MONTHS_RU[dt.month]}"
    else:
        time_str = "—"
        date_str = "—"

    text = (
        f"✅ Заказ выполнен!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📋 Заказ #{order_id}\n"
        f"👤 {updated_order.get('client_name', '—')}\n"
        f"🕐 {time_str} | {date_str}\n"
        f"💰 Сумма: {amount} ₽\n"
    )
    if bonus_spent > 0:
        text += f"🎁 Списано: {bonus_spent} ₽\n"
    if bonus_accrued > 0:
        text += f"⭐ Начислено: +{bonus_accrued} ₽\n"
    text += f"📊 Статус: ✅ выполнен\n"
    text += "━━━━━━━━━━━━━━━"

    await edit_home_message(callback, text, order_card_kb(order_id, client_id, "done"))
    await callback.answer("Заказ выполнен!")


@router.callback_query(F.data == "complete:cancel")
async def complete_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel order completion - return to order card."""
    data = await state.get_data()
    order_id = data.get("complete_order_id")

    await state.clear()

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    # Show order card
    order = await get_order_by_id(order_id, master.id)
    if not order:
        text = await build_home_text(master)
        await edit_home_message(callback, text, home_master_kb())
        await callback.answer("Отменено")
        return

    scheduled = order.get("scheduled_at", "")
    if scheduled:
        dt = datetime.fromisoformat(scheduled)
        time_str = dt.strftime("%H:%M")
        date_str = f"{dt.day} {MONTHS_RU[dt.month]}"
    else:
        time_str = "—"
        date_str = "—"

    status_map = {
        "new": "новый", "confirmed": "подтверждён", "done": "выполнен",
        "cancelled": "отменён", "moved": "перенесён",
    }
    status_emoji = {"new": "🆕", "confirmed": "📌", "done": "✅", "cancelled": "❌", "moved": "📅"}
    status = order.get("status", "")

    text = (
        f"📋 Заказ #{order['id']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {order.get('client_name', '—')}\n"
        f"📞 {order.get('client_phone', '—')}\n"
        f"📍 {order.get('address', '—')}\n"
        f"🕐 {time_str} | {date_str}\n"
        f"🛠 {order.get('services', '—')}\n"
        f"💰 Итого: {order.get('amount_total', 0) or '—'} ₽\n"
        f"📊 Статус: {status_emoji.get(status, '')} {status_map.get(status, status)}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, order_card_kb(order_id, order.get("client_id"), status))
    await callback.answer("Отменено")


# =============================================================================
# Move Order FSM
# =============================================================================

@router.callback_query(F.data.startswith("orders:move:"))
async def cb_orders_move(callback: CallbackQuery, state: FSMContext) -> None:
    """Start moving/rescheduling an order."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    order_id = int(callback.data.split(":")[2])
    order = await get_order_by_id(order_id, master.id)

    if not order:
        await callback.answer("Заказ не найден")
        return

    old_dt = datetime.fromisoformat(order.get("scheduled_at"))

    await state.update_data(
        move_order_id=order_id,
        move_old_dt=order.get("scheduled_at"),
        move_new_date=None,
        move_new_hour=None,
        move_new_minutes=None
    )

    today = date.today()
    old_day = old_dt.day
    old_month = MONTHS_RU[old_dt.month]
    old_time = old_dt.strftime("%H:%M")

    text = (
        "📅 Перенести заказ\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {order.get('client_name', '—')}\n"
        f"⏰ Текущее время: {old_day} {old_month} в {old_time}\n"
        "━━━━━━━━━━━━━━━\n"
        "Выберите новую дату:"
    )

    await edit_home_message(callback, text, order_calendar_kb(today.year, today.month, "move"))
    await state.set_state(MoveOrder.date)
    await callback.answer()


@router.callback_query(MoveOrder.date, F.data.regexp(r"^move:cal:\d+:\d+$"))
async def move_calendar_nav(callback: CallbackQuery, state: FSMContext) -> None:
    """Navigate calendar for move."""
    parts = callback.data.split(":")
    year = int(parts[2])
    month = int(parts[3])

    data = await state.get_data()
    old_dt_str = data.get("move_old_dt")
    old_dt = datetime.fromisoformat(old_dt_str)
    old_day = old_dt.day
    old_month = MONTHS_RU[old_dt.month]
    old_time = old_dt.strftime("%H:%M")

    text = (
        "📅 Перенести заказ\n"
        "━━━━━━━━━━━━━━━\n"
        f"⏰ Текущее время: {old_day} {old_month} в {old_time}\n"
        "━━━━━━━━━━━━━━━\n"
        "Выберите новую дату:"
    )

    await edit_home_message(callback, text, order_calendar_kb(year, month, "move"))
    await callback.answer()


@router.callback_query(MoveOrder.date, F.data.startswith("move:date:"))
async def move_select_date(callback: CallbackQuery, state: FSMContext) -> None:
    """Select new date for order."""
    date_str = callback.data.split(":")[2]
    await state.update_data(move_new_date=date_str)

    data = await state.get_data()
    old_dt_str = data.get("move_old_dt")
    old_dt = datetime.fromisoformat(old_dt_str)
    old_day = old_dt.day
    old_month = MONTHS_RU[old_dt.month]
    old_time = old_dt.strftime("%H:%M")

    new_date = date.fromisoformat(date_str)
    new_day = new_date.day
    new_month = MONTHS_RU[new_date.month]

    text = (
        "📅 Перенести заказ\n"
        "━━━━━━━━━━━━━━━\n"
        f"❌ Было: {old_day} {old_month} в {old_time}\n"
        f"✅ Новая дата: {new_day} {new_month}\n"
        "━━━━━━━━━━━━━━━\n"
        "Выберите час:"
    )

    await edit_home_message(callback, text, move_hour_kb())
    await state.set_state(MoveOrder.hour)
    await callback.answer()


@router.callback_query(MoveOrder.hour, F.data.startswith("move:hour:"))
async def move_select_hour(callback: CallbackQuery, state: FSMContext) -> None:
    """Select new hour for order."""
    hour = int(callback.data.split(":")[2])
    await state.update_data(move_new_hour=hour)

    text = (
        "📅 Перенести заказ\n"
        "━━━━━━━━━━━━━━━\n"
        "Выберите минуты:"
    )

    await edit_home_message(callback, text, move_minutes_kb(hour))
    await state.set_state(MoveOrder.minutes)
    await callback.answer()


@router.callback_query(MoveOrder.minutes, F.data.startswith("move:minutes:"))
async def move_select_minutes(callback: CallbackQuery, state: FSMContext) -> None:
    """Select new minutes, show confirmation."""
    minutes = int(callback.data.split(":")[2])
    await state.update_data(move_new_minutes=minutes)

    data = await state.get_data()
    old_dt_str = data.get("move_old_dt")
    old_dt = datetime.fromisoformat(old_dt_str)
    old_day = old_dt.day
    old_month = MONTHS_RU[old_dt.month]
    old_time = old_dt.strftime("%H:%M")

    new_date_str = data.get("move_new_date")
    new_date = date.fromisoformat(new_date_str)
    new_day = new_date.day
    new_month = MONTHS_RU[new_date.month]
    new_hour = data.get("move_new_hour")
    new_time = f"{new_hour}:{minutes:02d}"

    text = (
        "📅 Перенести заказ — Подтверждение\n"
        "━━━━━━━━━━━━━━━\n"
        f"❌ Было: {old_day} {old_month} в {old_time}\n"
        f"✅ Стало: {new_day} {new_month} в {new_time}\n"
        "━━━━━━━━━━━━━━━\n"
        "Подтвердить перенос?"
    )

    await edit_home_message(callback, text, move_confirm_kb())
    await state.set_state(MoveOrder.confirm)
    await callback.answer()


@router.callback_query(MoveOrder.confirm, F.data == "move:confirm:yes")
async def move_order_final(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Execute order move."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    order_id = data.get("move_order_id")
    old_dt_str = data.get("move_old_dt")
    old_dt = datetime.fromisoformat(old_dt_str)
    new_date_str = data.get("move_new_date")
    new_hour = data.get("move_new_hour")
    new_minutes = data.get("move_new_minutes")

    new_dt = datetime.fromisoformat(f"{new_date_str}T{new_hour:02d}:{new_minutes:02d}:00")

    # Update order
    await update_order_schedule(order_id, new_dt)

    # Handle confirmation status based on how far the new time is
    now = datetime.now()
    hours_until = (new_dt - now).total_seconds() / 3600

    if hours_until <= 24:
        # Auto-confirm: within 24h, no need for new reminder cycle
        await mark_order_confirmed_by_client(order_id)
    else:
        # Reset flags for new reminder cycle
        await reset_order_for_reconfirmation(order_id)

    # Get order details
    order = await get_order_by_id(order_id, master.id)

    # Update GC event if exists
    if order.get("gc_event_id"):
        try:
            await google_calendar.update_event(master.id, order.get("gc_event_id"), new_dt)
        except Exception as e:
            logger.error(f"GC update_event error: {e}")

    # Notify client
    client = await get_client_by_id(order.get("client_id"))
    if client and client.tg_id:
        await notifications.notify_order_moved(
            client=client,
            order={"scheduled_at": new_dt, "address": order.get("address")},
            master=master,
            old_dt=old_dt
        )

    await state.clear()

    # Show updated order card
    updated_order = await get_order_by_id(order_id, master.id)
    client_id = updated_order.get("client_id")
    status = updated_order.get("status", "")

    new_day = new_dt.day
    new_month = MONTHS_RU[new_dt.month]
    new_time = new_dt.strftime("%H:%M")

    status_map = {
        "new": "новый", "confirmed": "подтверждён", "done": "выполнен",
        "cancelled": "отменён", "moved": "перенесён",
    }
    status_emoji = {"new": "🆕", "confirmed": "📌", "done": "✅", "cancelled": "❌", "moved": "📅"}

    text = (
        f"✅ Заказ перенесён!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📋 Заказ #{order_id}\n"
        f"👤 {updated_order.get('client_name', '—')}\n"
        f"📍 {updated_order.get('address', '—')}\n"
        f"🕐 {new_time} | {new_day} {new_month}\n"
        f"🛠 {updated_order.get('services', '—')}\n"
        f"💰 Итого: {updated_order.get('amount_total', 0) or '—'} ₽\n"
        f"📊 Статус: {status_emoji.get(status, '')} {status_map.get(status, status)}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, order_card_kb(order_id, client_id, status))
    await callback.answer("Заказ перенесён!")


@router.callback_query(F.data == "move:cancel")
async def move_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel order move - return to order card."""
    data = await state.get_data()
    order_id = data.get("move_order_id")

    await state.clear()

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    # Show order card
    order = await get_order_by_id(order_id, master.id)
    if not order:
        text = await build_home_text(master)
        await edit_home_message(callback, text, home_master_kb())
        await callback.answer("Отменено")
        return

    scheduled = order.get("scheduled_at", "")
    if scheduled:
        dt = datetime.fromisoformat(scheduled)
        time_str = dt.strftime("%H:%M")
        date_str = f"{dt.day} {MONTHS_RU[dt.month]}"
    else:
        time_str = "—"
        date_str = "—"

    status_map = {
        "new": "новый", "confirmed": "подтверждён", "done": "выполнен",
        "cancelled": "отменён", "moved": "перенесён",
    }
    status_emoji = {"new": "🆕", "confirmed": "📌", "done": "✅", "cancelled": "❌", "moved": "📅"}
    status = order.get("status", "")

    text = (
        f"📋 Заказ #{order['id']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {order.get('client_name', '—')}\n"
        f"📞 {order.get('client_phone', '—')}\n"
        f"📍 {order.get('address', '—')}\n"
        f"🕐 {time_str} | {date_str}\n"
        f"🛠 {order.get('services', '—')}\n"
        f"💰 Итого: {order.get('amount_total', 0) or '—'} ₽\n"
        f"📊 Статус: {status_emoji.get(status, '')} {status_map.get(status, status)}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, order_card_kb(order_id, order.get("client_id"), status))
    await callback.answer("Отменено")


# =============================================================================
# Cancel Order FSM
# =============================================================================

@router.callback_query(F.data.startswith("orders:cancel:"))
async def cb_orders_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Start cancelling an order."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    order_id = int(callback.data.split(":")[2])
    order = await get_order_by_id(order_id, master.id)

    if not order:
        await callback.answer("Заказ не найден")
        return

    await state.update_data(
        cancel_order_id=order_id,
        cancel_reason=None
    )

    text = (
        "❌ Отменить заказ\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {order.get('client_name', '—')}\n"
        f"🛠 {order.get('services', '—')}\n"
        "━━━━━━━━━━━━━━━\n"
        "Выберите причину отмены:"
    )

    await edit_home_message(callback, text, cancel_reason_kb())
    await state.set_state(CancelOrder.reason)
    await callback.answer()


@router.callback_query(CancelOrder.reason, F.data.startswith("cancel:reason:"))
async def cancel_select_reason(callback: CallbackQuery, state: FSMContext) -> None:
    """Select cancel reason."""
    reason_type = callback.data.split(":")[2]

    reason_map = {
        "client": "Клиент отменил",
        "master": "Мастер не может",
        "skip": None
    }

    if reason_type == "custom":
        text = (
            "❌ Отменить заказ\n"
            "━━━━━━━━━━━━━━━\n"
            "Введите причину отмены:"
        )
        await edit_home_message(callback, text, stub_kb("cancel:back"))
        await state.set_state(CancelOrder.custom_reason)
        await callback.answer()
        return

    reason = reason_map.get(reason_type)
    await state.update_data(cancel_reason=reason)

    # Go to confirmation
    await go_to_cancel_confirm(callback, state, reason)
    await callback.answer()


@router.message(CancelOrder.custom_reason)
async def cancel_enter_custom_reason(message: Message, state: FSMContext, bot: Bot) -> None:
    """Enter custom cancel reason."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    reason = message.text.strip()[:500]
    await state.update_data(cancel_reason=reason)

    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    order_id = data.get("cancel_order_id")
    order = await get_order_by_id(order_id, master.id)

    reason_text = f"\n📝 Причина: {reason}" if reason else ""

    text = (
        "❌ Отменить заказ — Подтверждение\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {order.get('client_name', '—')}\n"
        f"🛠 {order.get('services', '—')}"
        f"{reason_text}\n"
        "━━━━━━━━━━━━━━━\n"
        "Подтвердить отмену?"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=cancel_confirm_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(CancelOrder.confirm)


async def go_to_cancel_confirm(callback: CallbackQuery, state: FSMContext, reason: str) -> None:
    """Go to cancel confirmation."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    order_id = data.get("cancel_order_id")
    order = await get_order_by_id(order_id, master.id)

    reason_text = f"\n📝 Причина: {reason}" if reason else ""

    text = (
        "❌ Отменить заказ — Подтверждение\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {order.get('client_name', '—')}\n"
        f"🛠 {order.get('services', '—')}"
        f"{reason_text}\n"
        "━━━━━━━━━━━━━━━\n"
        "Подтвердить отмену?"
    )

    await edit_home_message(callback, text, cancel_confirm_kb())
    await state.set_state(CancelOrder.confirm)


@router.callback_query(CancelOrder.confirm, F.data == "cancel:confirm:yes")
async def cancel_order_final(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Execute order cancellation."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    order_id = data.get("cancel_order_id")
    reason = data.get("cancel_reason")

    # Get order details
    order = await get_order_by_id(order_id, master.id)

    # Update order status
    await update_order_status(order_id, "cancelled", cancel_reason=reason)

    # Delete GC event if exists
    if order.get("gc_event_id"):
        try:
            await google_calendar.delete_event(master.id, order.get("gc_event_id"))
        except Exception as e:
            logger.error(f"GC delete_event error: {e}")

    # Notify client
    client = await get_client_by_id(order.get("client_id"))
    if client and client.tg_id:
        await notifications.notify_order_cancelled(
            client=client,
            order={
                "scheduled_at": order.get("scheduled_at"),
                "services": order.get("services", ""),
                "cancel_reason": reason
            },
            master=master
        )

    await state.clear()
    await state.update_data(current_screen="orders", orders_date=date.today().isoformat())

    # Show orders screen
    today = date.today()
    orders = await get_orders_today(master.id, all_statuses=True)

    day = today.day
    month = MONTHS_RU[today.month]

    text = (
        f"✅ Заказ отменён!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 Заказы — Сегодня, {day} {month}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, orders_kb(orders, today))
    await callback.answer("Заказ отменён!")


@router.callback_query(F.data == "cancel:back")
async def cancel_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to reason selection."""
    data = await state.get_data()
    order_id = data.get("cancel_order_id")

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    order = await get_order_by_id(order_id, master.id)

    text = (
        "❌ Отменить заказ\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 {order.get('client_name', '—')}\n"
        f"🛠 {order.get('services', '—')}\n"
        "━━━━━━━━━━━━━━━\n"
        "Выберите причину отмены:"
    )

    await edit_home_message(callback, text, cancel_reason_kb())
    await state.set_state(CancelOrder.reason)
    await callback.answer()


# =============================================================================
# Clients Section
# =============================================================================

@router.callback_query(F.data == "clients")
async def cb_clients(callback: CallbackQuery, state: FSMContext) -> None:
    """Show clients section with paginated list."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    await state.update_data(current_screen="clients", clients_page=1)

    clients, total = await get_clients_paginated(master.id, page=1)
    total_pages = max(1, (total + 9) // 10)

    text = (
        "👥 Клиенты\n"
        "━━━━━━━━━━━━━━━\n"
        "🔍 Введите часть имени/телефона\n"
        "для поиска или выберите из списка.\n"
        f"стр 1 из {total_pages}"
    )

    await edit_home_message(callback, text, clients_paginated_kb(clients, 1, total))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:page:"))
async def cb_clients_page(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle client list pagination."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    page = int(callback.data.split(":")[2])
    await state.update_data(clients_page=page)

    clients, total = await get_clients_paginated(master.id, page=page)
    total_pages = max(1, (total + 9) // 10)

    text = (
        "👥 Клиенты\n"
        "━━━━━━━━━━━━━━━\n"
        "🔍 Введите часть имени/телефона\n"
        "для поиска или выберите из списка.\n"
        f"стр {page} из {total_pages}"
    )

    await edit_home_message(callback, text, clients_paginated_kb(clients, page, total))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:view:"))
async def cb_client_view(callback: CallbackQuery, state: FSMContext) -> None:
    """View client card."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    client_id = int(callback.data.split(":")[2])
    client = await get_client_with_stats(master.id, client_id)

    if not client:
        await callback.answer("Клиент не найден")
        return

    birthday_str = client.get("birthday", "")
    if birthday_str:
        try:
            bd = date.fromisoformat(birthday_str)
            birthday_text = f"{bd.day} {MONTHS_RU[bd.month]}"
        except:
            birthday_text = "не указана"
    else:
        birthday_text = "не указана"

    text = (
        f"👤 {client.get('name', '—')}\n"
        f"📞 {client.get('phone', '—')}\n"
        f"🎂 {birthday_text}\n"
        f"💰 Бонусов: {client.get('bonus_balance', 0)} ₽\n"
        f"🛒 Заказов: {client.get('order_count', 0)} | Потрачено: {client.get('total_spent', 0)} ₽\n"
        f"📝 {client.get('note') or '—'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await state.update_data(current_client_id=client_id)
    await edit_home_message(callback, text, client_card_kb(client_id))
    await callback.answer()


ORDER_STATUS_ICONS = {
    "new": "🆕",
    "confirmed": "📌",
    "done": "✅",
    "cancelled": "❌",
    "moved": "📅",
}


@router.callback_query(F.data.startswith("clients:history:"))
async def cb_client_history(callback: CallbackQuery, state: FSMContext) -> None:
    """View client history with status icons."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    client_id = int(callback.data.split(":")[2])
    client = await get_client_with_stats(master.id, client_id)
    orders = await get_client_orders_history(master.id, client_id)

    if orders:
        def format_order(o):
            status = o.get("status", "")
            icon = ORDER_STATUS_ICONS.get(status, "•")
            scheduled = o.get("scheduled_at", "")[:10] if o.get("scheduled_at") else "—"
            services = o.get("services", "—")[:25] if o.get("services") else "—"
            amount = o.get("amount_total", 0)
            return f"{icon} {scheduled} — {services} | {amount} ₽"

        orders_text = "\n".join(format_order(o) for o in orders)
    else:
        orders_text = "История пуста"

    text = (
        f"📋 История — {client.get('name', 'Клиент')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{orders_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, client_history_kb(client_id))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:bonus:") & ~F.data.contains("add") & ~F.data.contains("sub"))
async def cb_client_bonus(callback: CallbackQuery, state: FSMContext) -> None:
    """View client bonus log with order references."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    client_id = int(callback.data.split(":")[2])
    client = await get_client_with_stats(master.id, client_id)
    bonus_log = await get_client_bonus_log(master.id, client_id)

    if bonus_log:
        def format_bonus(b):
            date_str = b.get("created_at", "")[:10] if b.get("created_at") else "—"
            amount = b.get("amount", 0)
            sign = "+" if amount > 0 else ""
            comment = b.get("comment", "—")
            order_id = b.get("order_id_display")
            if order_id:
                return f"• {date_str} {sign}{amount} — #{order_id} {comment}"
            return f"• {date_str} {sign}{amount} — {comment}"

        log_text = "\n".join(format_bonus(b) for b in bonus_log)
    else:
        log_text = "Операций пока нет"

    text = (
        f"🎁 Бонусы — {client.get('name', 'Клиент')}\n"
        f"Баланс: {client.get('bonus_balance', 0)} ₽\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{log_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, client_bonus_kb(client_id))
    await callback.answer()


# =============================================================================
# Client Add FSM (from Clients menu)
# =============================================================================

@router.callback_query(F.data == "clients:new")
async def cb_clients_new(callback: CallbackQuery, state: FSMContext) -> None:
    """Start adding new client."""
    text = (
        "👤 Новый клиент — Шаг 1/3\n"
        "━━━━━━━━━━━━━━━\n"
        "Введите имя клиента:"
    )
    await edit_home_message(callback, text, stub_kb("clients"))
    await state.set_state(ClientAdd.name)
    await callback.answer()


@router.message(ClientAdd.name)
async def client_add_name(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 1: Client name."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    name = message.text.strip()[:100]
    await state.update_data(add_client_name=name)

    try:
        await message.delete()
    except:
        pass

    text = (
        "👤 Новый клиент — Шаг 2/3\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {name}\n"
        "━━━━━━━━━━━━━━━\n"
        "📞 Введите телефон:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=stub_kb("clients")
            )
        except TelegramBadRequest:
            pass

    await state.set_state(ClientAdd.phone)


@router.message(ClientAdd.phone)
async def client_add_phone(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 2: Client phone."""
    import asyncio
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        await message.delete()
    except:
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
        except:
            pass
        return

    await state.update_data(add_client_phone=phone)

    data = await state.get_data()
    name = data.get("add_client_name")

    text = (
        "👤 Новый клиент — Шаг 3/3\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        "━━━━━━━━━━━━━━━\n"
        "🎂 Введите дату рождения (ДД.ММ.ГГГГ) или пропустите:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=skip_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(ClientAdd.birthday)


@router.message(ClientAdd.birthday)
async def client_add_birthday(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 3: Client birthday."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    birthday_text = message.text.strip()
    birthday = None

    try:
        from src.utils import parse_date
        birthday = parse_date(birthday_text)
    except:
        pass

    try:
        await message.delete()
    except:
        pass

    await finish_client_add(state, master, bot, message.chat.id, birthday)


@router.callback_query(ClientAdd.birthday, F.data == "skip")
async def client_add_birthday_skip(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Skip birthday."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    await finish_client_add(state, master, bot, callback.message.chat.id, None)
    await callback.answer()


async def finish_client_add(state: FSMContext, master, bot: Bot, chat_id: int, birthday: str) -> None:
    """Finish adding client and show clients screen."""
    data = await state.get_data()
    name = data.get("add_client_name")
    phone = data.get("add_client_phone")

    # Create client
    client = await create_client(
        name=name,
        phone=phone,
        birthday=birthday,
        registered_via=master.id
    )

    # Link to master
    await link_client_to_master(master.id, client.id)

    await state.clear()
    await state.update_data(current_screen="clients")

    # Show clients screen
    text = (
        f"✅ Клиент «{name}» создан!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👥 Клиенты\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔍 Введите имя или телефон для поиска:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=clients_kb()
            )
        except TelegramBadRequest:
            pass


# =============================================================================
# Client Edit FSM
# =============================================================================

CLIENT_FIELDS = {
    "name": ("Имя", "name"),
    "phone": ("Телефон", "phone"),
    "birthday": ("Дата рождения", "birthday"),
}


@router.callback_query(F.data.regexp(r"^clients:edit:\d+$"))
async def cb_clients_edit_menu(callback: CallbackQuery) -> None:
    """Show client edit menu."""
    client_id = int(callback.data.split(":")[2])
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    client = await get_client_with_stats(master.id, client_id)
    if not client:
        await callback.answer("Клиент не найден")
        return

    text = (
        f"✏️ Редактирование — {client.get('name', 'Клиент')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 Имя: {client.get('name', '—')}\n"
        f"📞 Телефон: {client.get('phone', '—')}\n"
        f"🎂 ДР: {client.get('birthday', '—') or '—'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, client_edit_kb(client_id))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^clients:edit:(name|phone|birthday):\d+$"))
async def cb_clients_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing a client field."""
    parts = callback.data.split(":")
    field = parts[2]
    client_id = int(parts[3])

    if field not in CLIENT_FIELDS:
        await callback.answer("Неизвестное поле")
        return

    field_name, db_field = CLIENT_FIELDS[field]
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    client = await get_client_with_stats(master.id, client_id)
    if not client:
        await callback.answer("Клиент не найден")
        return

    await state.update_data(
        edit_client_id=client_id,
        edit_client_field=field,
        edit_client_db_field=db_field,
    )

    hint = ""
    if field == "birthday":
        hint = "\n(формат: ДД.ММ.ГГГГ)"

    text = (
        f"✏️ Изменить {field_name}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Введите новое значение:{hint}"
    )

    await edit_home_message(callback, text, stub_kb(f"clients:edit:{client_id}"))
    await state.set_state(ClientEdit.waiting_value)
    await callback.answer()


@router.message(ClientEdit.waiting_value)
async def client_edit_value(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save edited client field value."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    client_id = data.get("edit_client_id")
    field = data.get("edit_client_field")
    db_field = data.get("edit_client_db_field")

    value = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    # Validate phone if needed
    if field == "phone":
        normalized = normalize_phone(value)
        if not normalized:
            if master.home_message_id:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=master.home_message_id,
                        text="❌ Неверный формат номера.\nВведите с кодом страны: +7..., +995..., +380...",
                        reply_markup=stub_kb(f"clients:edit:{client_id}")
                    )
                except TelegramBadRequest:
                    pass
            return
        value = normalized

    # Parse birthday if needed
    if field == "birthday":
        try:
            from src.utils import parse_date
            value = parse_date(value)
        except:
            # Invalid date format - show error
            if master.home_message_id:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=master.home_message_id,
                        text="❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ",
                        reply_markup=stub_kb(f"clients:edit:{client_id}")
                    )
                except TelegramBadRequest:
                    pass
            return

    # Update client
    await update_client(client_id, **{db_field: value})

    await state.clear()

    # Show updated client card
    client = await get_client_with_stats(master.id, client_id)

    birthday_str = client.get("birthday", "")
    if birthday_str:
        try:
            bd = date.fromisoformat(birthday_str)
            birthday_text = f"{bd.day} {MONTHS_RU[bd.month]}"
        except:
            birthday_text = "не указана"
    else:
        birthday_text = "не указана"

    text = (
        f"✅ Сохранено!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {client.get('name', '—')}\n"
        f"📞 {client.get('phone', '—')}\n"
        f"🎂 {birthday_text}\n"
        f"💰 Бонусов: {client.get('bonus_balance', 0)} ₽\n"
        f"🛒 Заказов: {client.get('order_count', 0)} | Потрачено: {client.get('total_spent', 0)} ₽\n"
        f"📝 {client.get('note') or '—'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=client_card_kb(client_id)
            )
        except TelegramBadRequest:
            pass


# =============================================================================
# Client Note FSM
# =============================================================================

@router.callback_query(F.data.startswith("clients:note:"))
async def cb_clients_note(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing client note."""
    client_id = int(callback.data.split(":")[2])
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    client = await get_client_with_stats(master.id, client_id)
    if not client:
        await callback.answer("Клиент не найден")
        return

    current_note = client.get("note") or ""

    await state.update_data(note_client_id=client_id)

    text = (
        f"📝 Заметка — {client.get('name', 'Клиент')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Текущая: {current_note or '(пусто)'}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Введите новую заметку\n"
        f"или «-» для удаления:"
    )

    await edit_home_message(callback, text, stub_kb(f"clients:view:{client_id}"))
    await state.set_state(ClientNote.waiting_note)
    await callback.answer()


@router.message(ClientNote.waiting_note)
async def client_note_value(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save client note."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    client_id = data.get("note_client_id")

    note_text = message.text.strip()

    try:
        await message.delete()
    except:
        pass

    # Delete note if "-"
    if note_text == "-":
        note_text = None

    # Update note
    await update_client_note(master.id, client_id, note_text)

    await state.clear()

    # Show updated client card
    client = await get_client_with_stats(master.id, client_id)

    birthday_str = client.get("birthday", "")
    if birthday_str:
        try:
            bd = date.fromisoformat(birthday_str)
            birthday_text = f"{bd.day} {MONTHS_RU[bd.month]}"
        except:
            birthday_text = "не указана"
    else:
        birthday_text = "не указана"

    text = (
        f"✅ Заметка сохранена!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {client.get('name', '—')}\n"
        f"📞 {client.get('phone', '—')}\n"
        f"🎂 {birthday_text}\n"
        f"💰 Бонусов: {client.get('bonus_balance', 0)} ₽\n"
        f"🛒 Заказов: {client.get('order_count', 0)} | Потрачено: {client.get('total_spent', 0)} ₽\n"
        f"📝 {client.get('note') or '—'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=client_card_kb(client_id)
            )
        except TelegramBadRequest:
            pass


# =============================================================================
# Manual Bonus FSM
# =============================================================================

@router.callback_query(F.data.startswith("clients:bonus:add:"))
async def cb_clients_bonus_add(callback: CallbackQuery, state: FSMContext) -> None:
    """Start adding bonus."""
    client_id = int(callback.data.split(":")[3])
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    client = await get_client_with_stats(master.id, client_id)
    if not client:
        await callback.answer("Клиент не найден")
        return

    await state.update_data(
        bonus_client_id=client_id,
        bonus_operation="add"
    )

    text = (
        f"➕ Начисление бонусов — {client.get('name', 'Клиент')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Баланс: {client.get('bonus_balance', 0)} ₽\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Введите сумму для начисления:"
    )

    await edit_home_message(callback, text, stub_kb(f"clients:bonus:{client_id}"))
    await state.set_state(BonusManual.waiting_amount)
    await callback.answer()


@router.callback_query(F.data.startswith("clients:bonus:sub:"))
async def cb_clients_bonus_sub(callback: CallbackQuery, state: FSMContext) -> None:
    """Start subtracting bonus."""
    client_id = int(callback.data.split(":")[3])
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    client = await get_client_with_stats(master.id, client_id)
    if not client:
        await callback.answer("Клиент не найден")
        return

    await state.update_data(
        bonus_client_id=client_id,
        bonus_operation="sub"
    )

    text = (
        f"➖ Списание бонусов — {client.get('name', 'Клиент')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Баланс: {client.get('bonus_balance', 0)} ₽\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Введите сумму для списания:"
    )

    await edit_home_message(callback, text, stub_kb(f"clients:bonus:{client_id}"))
    await state.set_state(BonusManual.waiting_amount)
    await callback.answer()


@router.message(BonusManual.waiting_amount)
async def bonus_manual_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    """Process bonus amount."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("Введите положительное целое число")
        return

    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    client_id = data.get("bonus_client_id")
    operation = data.get("bonus_operation")

    await state.update_data(bonus_amount=amount)

    client = await get_client_with_stats(master.id, client_id)
    op_text = "начисления" if operation == "add" else "списания"
    sign = "+" if operation == "add" else "-"

    text = (
        f"💬 Комментарий к {op_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Сумма: {sign}{amount} ₽\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Введите комментарий или пропустите:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=skip_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(BonusManual.waiting_comment)


@router.message(BonusManual.waiting_comment)
async def bonus_manual_comment(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save bonus with comment."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    comment = message.text.strip()[:200]

    try:
        await message.delete()
    except:
        pass

    await finish_manual_bonus(state, master, bot, message.chat.id, comment)


@router.callback_query(BonusManual.waiting_comment, F.data == "skip")
async def bonus_manual_comment_skip(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Skip comment."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    await finish_manual_bonus(state, master, bot, callback.message.chat.id, None)
    await callback.answer()


async def finish_manual_bonus(state: FSMContext, master, bot: Bot, chat_id: int, comment: str) -> None:
    """Finish manual bonus operation."""
    data = await state.get_data()
    client_id = data.get("bonus_client_id")
    amount = data.get("bonus_amount")
    operation = data.get("bonus_operation")

    # Apply sign based on operation
    if operation == "sub":
        amount = -amount

    # Perform transaction
    new_balance = await manual_bonus_transaction(master.id, client_id, amount, comment)

    await state.clear()

    # Show bonus log
    client = await get_client_with_stats(master.id, client_id)
    bonus_log = await get_client_bonus_log(master.id, client_id)

    op_text = "начислено" if operation == "add" else "списано"

    if bonus_log:
        log_text = "\n".join(
            f"• {b.get('created_at', '')[:10] if b.get('created_at') else '—'} "
            f"{'+' if b.get('amount', 0) > 0 else ''}{b.get('amount', 0)} — {b.get('comment', '—')}"
            for b in bonus_log[:10]
        )
    else:
        log_text = "Операций пока нет"

    text = (
        f"✅ Бонусы {op_text}!\n"
        f"🎁 Баланс: {new_balance} ₽\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{log_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=client_bonus_kb(client_id)
            )
        except TelegramBadRequest:
            pass


# =============================================================================
# Create Order from Client Card
# =============================================================================

@router.callback_query(F.data.startswith("clients:order:"))
async def cb_clients_order(callback: CallbackQuery, state: FSMContext) -> None:
    """Start creating order from client card - skip client search, go to address."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    client_id = int(callback.data.split(":")[2])
    client = await get_client_by_id(client_id)

    if not client:
        await callback.answer("Клиент не найден")
        return

    # Initialize order data with client already selected
    last_address = await get_last_client_address(master.id, client_id)

    await state.update_data(
        order_master_id=master.id,
        order_client_id=client_id,
        order_client_name=client.name,
        order_address=None,
        order_date=None,
        order_hour=None,
        order_minutes=None,
        order_services=[],
        order_custom_services=[],
        order_amount=None,
        order_last_address=last_address,
    )

    if last_address:
        text = (
            "📋 Новый заказ — Шаг 2/7\n"
            "━━━━━━━━━━━━━━━\n"
            f"👤 Клиент: {client.name}\n"
            "━━━━━━━━━━━━━━━\n"
            "📍 Выберите адрес или введите новый:"
        )
    else:
        text = (
            "📋 Новый заказ — Шаг 2/7\n"
            "━━━━━━━━━━━━━━━\n"
            f"👤 Клиент: {client.name}\n"
            "━━━━━━━━━━━━━━━\n"
            "📍 Введите адрес:"
        )

    await edit_home_message(callback, text, order_address_kb(last_address))
    await state.set_state(CreateOrder.address)
    await callback.answer()


# Handle text search when on clients screen (not in any FSM state)
# StateFilter(None) ensures this only matches when there's NO active FSM state
@router.message(F.text, StateFilter(None))
async def handle_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle text input for search (only when not in FSM state)."""
    data = await state.get_data()
    current_screen = data.get("current_screen")

    if current_screen == "clients":
        tg_id = message.from_user.id
        master = await get_master_by_tg_id(tg_id)

        if not master:
            return

        query = message.text.strip()
        results = await search_clients(master.id, query)

        # Delete search message
        try:
            await message.delete()
        except:
            pass

        if results:
            text = (
                f"👥 Результаты поиска: «{query}»\n"
                f"━━━━━━━━━━━━━━━"
            )
        else:
            text = (
                f"👥 Ничего не найдено: «{query}»\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Попробуйте другой запрос"
            )

        # Update home message
        if master.home_message_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=master.home_message_id,
                    text=text,
                    reply_markup=clients_kb(results)
                )
            except TelegramBadRequest:
                pass


# =============================================================================
# Marketing Section
# =============================================================================

@router.callback_query(F.data == "marketing")
async def cb_marketing(callback: CallbackQuery, state: FSMContext) -> None:
    """Show marketing section with active promos."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    await state.clear()
    await state.update_data(current_screen="marketing")

    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(
            f"• {p.title}" for p in promos
        )
    else:
        promos_text = "Активных акций нет"

    text = (
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, marketing_kb(promos))
    await callback.answer()


# =============================================================================
# Broadcast FSM
# =============================================================================

SEGMENT_NAMES = {
    "all": "Все клиенты",
    "inactive_3m": "Не приходили 3+ месяца",
    "inactive_6m": "Не приходили 6+ месяцев",
    "new_30d": "Новые за 30 дней",
}


@router.callback_query(F.data == "marketing:broadcast")
async def cb_marketing_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Start broadcast flow - Step 1: Text."""
    text = (
        "📨 Новая рассылка\n"
        "━━━━━━━━━━━━━━━\n"
        "Введите текст сообщения:"
    )

    await edit_home_message(callback, text, broadcast_cancel_kb())
    await state.set_state(BroadcastFSM.text)
    await callback.answer()


@router.message(BroadcastFSM.text)
async def broadcast_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 1: Save broadcast text."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    text_content = message.text.strip()
    await state.update_data(broadcast_text=text_content)

    try:
        await message.delete()
    except:
        pass

    text = (
        "📨 Новая рассылка\n"
        "━━━━━━━━━━━━━━━\n"
        "Прикрепить фото или видео? (необязательно)\n\n"
        "Отправьте фото/видео или нажмите «Пропустить»:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=broadcast_media_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(BroadcastFSM.media)


@router.message(BroadcastFSM.media, F.photo)
async def broadcast_media_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 2: Save photo."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    file_id = message.photo[-1].file_id  # Largest photo
    await state.update_data(broadcast_file_id=file_id, broadcast_media_type="photo")

    try:
        await message.delete()
    except:
        pass

    await show_broadcast_segment_step(bot, master, message.chat.id, state)


@router.message(BroadcastFSM.media, F.video)
async def broadcast_media_video(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 2: Save video."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    file_id = message.video.file_id
    await state.update_data(broadcast_file_id=file_id, broadcast_media_type="video")

    try:
        await message.delete()
    except:
        pass

    await show_broadcast_segment_step(bot, master, message.chat.id, state)


@router.callback_query(BroadcastFSM.media, F.data == "broadcast:media:skip")
async def broadcast_media_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 2: Skip media."""
    await state.update_data(broadcast_file_id=None, broadcast_media_type=None)

    text = (
        "📨 Новая рассылка\n"
        "━━━━━━━━━━━━━━━\n"
        "Кому отправить?"
    )

    await edit_home_message(callback, text, broadcast_segment_kb())
    await state.set_state(BroadcastFSM.segment)
    await callback.answer()


async def show_broadcast_segment_step(bot: Bot, master, chat_id: int, state: FSMContext) -> None:
    """Show segment selection step."""
    text = (
        "📨 Новая рассылка\n"
        "━━━━━━━━━━━━━━━\n"
        "📎 Медиа прикреплено\n"
        "━━━━━━━━━━━━━━━\n"
        "Кому отправить?"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=broadcast_segment_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(BroadcastFSM.segment)


@router.callback_query(BroadcastFSM.segment, F.data.startswith("broadcast:segment:"))
async def broadcast_select_segment(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Select segment and show preview."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    segment = callback.data.split(":")[2]
    await state.update_data(broadcast_segment=segment)

    # Get recipient count
    count = await get_broadcast_recipients_count(master.id, segment)

    if count == 0:
        text = (
            "📨 Рассылка\n"
            "━━━━━━━━━━━━━━━\n"
            "В этом сегменте нет клиентов с Telegram."
        )
        await edit_home_message(callback, text, broadcast_no_recipients_kb())
        await state.clear()
        await callback.answer()
        return

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    has_media = data.get("broadcast_file_id") is not None
    segment_name = SEGMENT_NAMES.get(segment, segment)

    media_text = "📎 + медиа\n" if has_media else ""

    text = (
        f"📨 Предпросмотр рассылки\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{broadcast_text}\n"
        f"{media_text}"
        f"━━━━━━━━━━━━━━━\n"
        f"Получателей: {count} клиентов\n"
        f"Сегмент: {segment_name}"
    )

    await edit_home_message(callback, text, broadcast_confirm_kb())
    await state.set_state(BroadcastFSM.confirm)
    await callback.answer()


@router.callback_query(BroadcastFSM.confirm, F.data == "broadcast:send")
async def broadcast_send(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Step 4: Send broadcast."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    file_id = data.get("broadcast_file_id")
    media_type = data.get("broadcast_media_type")
    segment = data.get("broadcast_segment", "all")

    # Show sending message
    await edit_home_message(callback, "📤 Отправка рассылки...", None)
    await callback.answer()

    # Get recipients
    recipients = await get_broadcast_recipients(master.id, segment)

    # Need client_bot to send messages
    from src.config import CLIENT_BOT_TOKEN
    from aiogram.types import BufferedInputFile
    import aiohttp

    client_bot = Bot(token=CLIENT_BOT_TOKEN)

    # If there's media, download it first (file_id is bot-specific)
    media_bytes = None
    if file_id:
        try:
            file_info = await bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{MASTER_BOT_TOKEN}/{file_info.file_path}"
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    if resp.status == 200:
                        media_bytes = await resp.read()
        except Exception as e:
            logger.error(f"Broadcast: failed to download media: {e}")
            file_id = None  # Fallback to text-only

    sent = 0
    failed = 0

    for client in recipients:
        try:
            if media_bytes:
                if media_type == "photo":
                    await client_bot.send_photo(
                        chat_id=client["tg_id"],
                        photo=BufferedInputFile(media_bytes, filename="broadcast.jpg"),
                        caption=broadcast_text
                    )
                else:
                    await client_bot.send_video(
                        chat_id=client["tg_id"],
                        video=BufferedInputFile(media_bytes, filename="broadcast.mp4"),
                        caption=broadcast_text
                    )
            else:
                await client_bot.send_message(
                    chat_id=client["tg_id"],
                    text=broadcast_text
                )
            sent += 1
            await asyncio.sleep(0.05)  # 50ms pause
        except TelegramForbiddenError:
            logger.warning(f"Broadcast: client {client['tg_id']} blocked the bot")
            failed += 1
        except Exception as e:
            logger.error(f"Broadcast: failed to send to {client['tg_id']}: {e}")
            failed += 1

    await client_bot.session.close()

    # Save campaign
    await save_campaign(
        master_id=master.id,
        campaign_type="broadcast",
        title=None,
        text=broadcast_text,
        active_from=None,
        active_to=None,
        sent_count=sent,
        segment=segment
    )

    await state.clear()
    await state.update_data(current_screen="marketing")

    # Show marketing screen
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"✅ Рассылка отправлена!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Отправлено: {sent}\n"
        f"Не доставлено: {failed}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    try:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=master.home_message_id,
            text=text,
            reply_markup=marketing_kb(promos)
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "broadcast:cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel broadcast."""
    await state.clear()

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, marketing_kb(promos))
    await callback.answer("Отменено")


# =============================================================================
# Promo FSM
# =============================================================================

@router.callback_query(F.data == "marketing:promo:new")
async def cb_marketing_promo_new(callback: CallbackQuery, state: FSMContext) -> None:
    """Start promo creation - Step 1: Title."""
    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        "Введите название акции:"
    )

    await edit_home_message(callback, text, promo_cancel_kb())
    await state.set_state(PromoFSM.title)
    await callback.answer()


@router.message(PromoFSM.title)
async def promo_title(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 1: Save promo title."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    title = message.text.strip()[:100]
    await state.update_data(promo_title=title)

    try:
        await message.delete()
    except:
        pass

    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        "━━━━━━━━━━━━━━━\n"
        "Введите описание акции\n"
        "(условия, выгода для клиента):"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=promo_cancel_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(PromoFSM.description)


@router.message(PromoFSM.description)
async def promo_description(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 2: Save promo description."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    description = message.text.strip()[:500]
    await state.update_data(promo_description=description)

    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    title = data.get("promo_title")

    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Описание: {description[:50]}...\n"
        "━━━━━━━━━━━━━━━\n"
        "Дата начала акции (например: 01.03.2026)\n"
        "или нажмите «Сегодня»:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=promo_date_from_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(PromoFSM.date_from)


@router.callback_query(PromoFSM.date_from, F.data == "promo:date_from:today")
async def promo_date_from_today(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Set start date to today."""
    today = date.today().isoformat()
    await state.update_data(promo_date_from=today)

    data = await state.get_data()
    title = data.get("promo_title")

    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Начало: сегодня\n"
        "━━━━━━━━━━━━━━━\n"
        "Дата окончания акции (например: 31.03.2026):"
    )

    await edit_home_message(callback, text, promo_cancel_kb())
    await state.set_state(PromoFSM.date_to)
    await callback.answer()


@router.message(PromoFSM.date_from)
async def promo_date_from_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 3: Parse start date."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        from src.utils import parse_date
        date_from_obj = parse_date(message.text.strip())
        if not date_from_obj:
            raise ValueError("Invalid date")
        date_from = date_from_obj.isoformat()
    except:
        await message.answer("Неверный формат даты. Используйте ДД.ММ.ГГГГ")
        return

    await state.update_data(promo_date_from=date_from)

    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    title = data.get("promo_title")

    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Начало: {date_from}\n"
        "━━━━━━━━━━━━━━━\n"
        "Дата окончания акции (например: 31.03.2026):"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=promo_cancel_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(PromoFSM.date_to)


@router.message(PromoFSM.date_to)
async def promo_date_to_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 4: Parse end date and show confirmation."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        from src.utils import parse_date
        date_to_obj = parse_date(message.text.strip())
        if not date_to_obj:
            raise ValueError("Invalid date")
        date_to = date_to_obj.isoformat()
    except:
        await message.answer("Неверный формат даты. Используйте ДД.ММ.ГГГГ")
        return

    data = await state.get_data()
    date_from = data.get("promo_date_from")
    today = date.today().isoformat()

    # Validate: end date must be >= today and >= start date
    if date_to < today:
        await message.answer("Дата окончания не может быть в прошлом")
        return
    if date_to < date_from:
        await message.answer("Дата окончания должна быть позже даты начала")
        return

    await state.update_data(promo_date_to=date_to)

    try:
        await message.delete()
    except:
        pass

    title = data.get("promo_title")
    description = data.get("promo_description")

    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Описание: {description}\n"
        f"Период: {date_from} — {date_to}\n"
        "━━━━━━━━━━━━━━━\n"
        "Разослать уведомление всем клиентам?"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=promo_confirm_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(PromoFSM.confirm)


@router.callback_query(PromoFSM.confirm, F.data == "promo:confirm:broadcast")
async def promo_confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Step 5: Create promo and broadcast."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    title = data.get("promo_title")
    description = data.get("promo_description")
    date_from = data.get("promo_date_from")
    date_to = data.get("promo_date_to")

    # Show sending message
    await edit_home_message(callback, "📤 Создание акции и отправка уведомлений...", None)
    await callback.answer()

    # Get recipients (all clients with notify_marketing)
    recipients = await get_broadcast_recipients(master.id, "all")

    # Send notifications via client_bot
    from src.config import CLIENT_BOT_TOKEN
    client_bot = Bot(token=CLIENT_BOT_TOKEN)

    sent = 0

    promo_text = (
        f"🎁 Новая акция от {master.name}!\n\n"
        f"{title}\n"
        f"{description}\n\n"
        f"📅 Действует: {date_from} — {date_to}"
    )

    for client in recipients:
        try:
            await client_bot.send_message(
                chat_id=client["tg_id"],
                text=promo_text
            )
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass

    await client_bot.session.close()

    # Save campaign
    await save_campaign(
        master_id=master.id,
        campaign_type="promo",
        title=title,
        text=description,
        active_from=date_from,
        active_to=date_to,
        sent_count=sent
    )

    await state.clear()
    await state.update_data(current_screen="marketing")

    # Show marketing screen
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"✅ Акция создана!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Период: {date_from} — {date_to}\n"
        f"Уведомлено клиентов: {sent}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    try:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=master.home_message_id,
            text=text,
            reply_markup=marketing_kb(promos)
        )
    except TelegramBadRequest:
        pass


@router.callback_query(PromoFSM.confirm, F.data == "promo:confirm:save")
async def promo_confirm_save(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 5: Create promo without broadcast."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    title = data.get("promo_title")
    description = data.get("promo_description")
    date_from = data.get("promo_date_from")
    date_to = data.get("promo_date_to")

    # Save campaign without broadcast
    await save_campaign(
        master_id=master.id,
        campaign_type="promo",
        title=title,
        text=description,
        active_from=date_from,
        active_to=date_to,
        sent_count=0
    )

    await state.clear()
    await state.update_data(current_screen="marketing")

    # Show marketing screen
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"✅ Акция создана!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Период: {date_from} — {date_to}\n"
        f"Уведомления не отправлялись\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, marketing_kb(promos))
    await callback.answer()


@router.callback_query(F.data == "promo:cancel")
async def promo_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel promo creation."""
    await state.clear()

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, marketing_kb(promos))
    await callback.answer("Отменено")


# =============================================================================
# Promo Card and Management
# =============================================================================

@router.callback_query(F.data.startswith("marketing:promo:view:"))
async def cb_promo_view(callback: CallbackQuery) -> None:
    """View promo card."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    promo_id = int(callback.data.split(":")[3])
    promo = await get_promo_by_id(promo_id, master.id)

    if not promo:
        await callback.answer("Акция не найдена")
        return

    text = (
        f"🎁 {promo.title}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promo.text}\n\n"
        f"📅 {promo.active_from} — {promo.active_to}\n"
        f"👥 Уведомлено клиентов: {promo.sent_count or 0}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, promo_card_kb(promo_id))
    await callback.answer()


@router.callback_query(F.data.startswith("marketing:promo:end:") & ~F.data.contains("confirm"))
async def cb_promo_end(callback: CallbackQuery) -> None:
    """Confirm promo deactivation."""
    promo_id = int(callback.data.split(":")[3])

    text = (
        "❌ Завершить акцию?\n"
        "━━━━━━━━━━━━━━━\n"
        "Акция будет убрана из активных."
    )

    await edit_home_message(callback, text, promo_end_confirm_kb(promo_id))
    await callback.answer()


@router.callback_query(F.data.startswith("marketing:promo:end:confirm:"))
async def cb_promo_end_confirm(callback: CallbackQuery) -> None:
    """Deactivate promo."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    promo_id = int(callback.data.split(":")[4])
    await deactivate_promo(promo_id, master.id)

    # Return to marketing
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ Акция завершена\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, marketing_kb(promos))
    await callback.answer("Акция завершена")


# =============================================================================
# Reports Section
# =============================================================================

@router.callback_query(F.data == "reports")
async def cb_reports(callback: CallbackQuery, state: FSMContext) -> None:
    """Show reports for current month."""
    await show_reports(callback, state, "month")


@router.callback_query(F.data == "reports:today")
async def cb_reports_today(callback: CallbackQuery, state: FSMContext) -> None:
    """Show reports for today."""
    await show_reports(callback, state, "today")


@router.callback_query(F.data == "reports:week")
async def cb_reports_week(callback: CallbackQuery, state: FSMContext) -> None:
    """Show reports for week."""
    await show_reports(callback, state, "week")


@router.callback_query(F.data == "reports:month")
async def cb_reports_month(callback: CallbackQuery, state: FSMContext) -> None:
    """Show reports for month."""
    await show_reports(callback, state, "month")


@router.callback_query(F.data == "reports:period")
async def cb_reports_period(callback: CallbackQuery, state: FSMContext) -> None:
    """Start custom period selection FSM."""
    await state.set_state(ReportPeriodFSM.date_from)
    text = (
        "📅 Произвольный период\n\n"
        "Введите дату начала периода\n"
        "(например: 01.03.2026):"
    )
    await edit_home_message(callback, text, report_period_cancel_kb())
    await callback.answer()


@router.message(ReportPeriodFSM.date_from)
async def fsm_report_date_from(message: Message, state: FSMContext) -> None:
    """Handle date_from input for custom period."""
    from src.utils import parse_date

    date_from = parse_date(message.text.strip())
    if not date_from:
        await message.answer(
            "❌ Неверный формат даты.\n"
            "Введите дату в формате ДД.ММ.ГГГГ\n"
            "(например: 01.03.2026):",
            reply_markup=report_period_cancel_kb()
        )
        return

    await state.update_data(report_date_from=date_from.isoformat())
    await state.set_state(ReportPeriodFSM.date_to)

    await message.answer(
        "Введите дату окончания периода\n"
        "(например: 31.03.2026):",
        reply_markup=report_period_cancel_kb()
    )


@router.message(ReportPeriodFSM.date_to)
async def fsm_report_date_to(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle date_to input for custom period."""
    from src.utils import parse_date

    date_to = parse_date(message.text.strip())
    if not date_to:
        await message.answer(
            "❌ Неверный формат даты.\n"
            "Введите дату в формате ДД.ММ.ГГГГ\n"
            "(например: 31.03.2026):",
            reply_markup=report_period_cancel_kb()
        )
        return

    data = await state.get_data()
    date_from = date.fromisoformat(data["report_date_from"])

    # Validate: date_to >= date_from
    if date_to < date_from:
        await message.answer(
            "❌ Дата окончания не может быть раньше даты начала.\n"
            "Введите корректную дату окончания:",
            reply_markup=report_period_cancel_kb()
        )
        return

    # Validate: period not more than 1 year
    if (date_to - date_from).days > 365:
        await message.answer(
            "❌ Период не может превышать 1 год.\n"
            "Введите дату окончания не более чем через год от начала:",
            reply_markup=report_period_cancel_kb()
        )
        return

    await state.clear()

    # Get master and show report
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)
    home_message_id = data.get("home_message_id")

    # Build report text inline since we can't use show_reports (no callback)
    report_data = await get_reports(master.id, date_from, date_to)

    # Format period text
    if date_from.year == date_to.year:
        period_text = f"{date_from.strftime('%d.%m')} — {date_to.strftime('%d.%m.%Y')}"
    else:
        period_text = f"{date_from.strftime('%d.%m.%Y')} — {date_to.strftime('%d.%m.%Y')}"

    # Build top services text (by popularity)
    top_services_text = ""
    if report_data["top_services"] and report_data["order_count"] > 0:
        lines = []
        for s in report_data["top_services"]:
            cnt = s["count"]
            if cnt == 1:
                times_word = "раз"
            elif 2 <= cnt <= 4:
                times_word = "раза"
            else:
                times_word = "раз"
            lines.append(f"- {s['name']} — {cnt} {times_word}")
        top_services_text = "\n".join(lines)

    # Build top orders text (by amount)
    top_orders_text = ""
    if report_data.get("top_orders") and report_data["order_count"] > 0:
        lines = []
        for o in report_data["top_orders"]:
            order_date = datetime.fromisoformat(o["date"]).strftime("%d.%m")
            lines.append(f"- {o['amount']:,} ₽ — {o['client_name']} ({order_date})".replace(",", " "))
        top_orders_text = "\n".join(lines)

    # Build report text
    if report_data["order_count"] == 0:
        text = (
            f"📊 Отчёты — {period_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"За этот период заказов нет.\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Выручка: 0 ₽\n"
            f"🛒 Заказов выполнено: 0\n"
            f"👥 Новых клиентов: {report_data['new_clients']}\n"
            f"🔄 Повторных клиентов: 0\n"
            f"🧾 Средний чек: 0 ₽\n"
            f"📋 Всего клиентов в базе: {report_data['total_clients']}\n"
            f"━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            f"📊 Отчёты — {period_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Выручка: {report_data['revenue']:,} ₽\n"
            f"🛒 Заказов выполнено: {report_data['order_count']}\n"
            f"👥 Новых клиентов: {report_data['new_clients']}\n"
            f"🔄 Повторных клиентов: {report_data['repeat_clients']}\n"
            f"🧾 Средний чек: {report_data['avg_check']:,} ₽\n"
            f"📋 Всего клиентов в базе: {report_data['total_clients']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🏆 Топ услуг по популярности:\n"
            f"{top_services_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Топ заказов по сумме:\n"
            f"{top_orders_text}\n"
            f"━━━━━━━━━━━━━━━"
        ).replace(",", " ")

    # Try to edit home message, fallback to send new
    if home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=home_message_id,
                text=text,
                reply_markup=reports_kb("custom")
            )
        except TelegramBadRequest:
            sent = await message.answer(text, reply_markup=reports_kb("custom"))
            await save_master_home_message_id(master.id, sent.message_id)
    else:
        sent = await message.answer(text, reply_markup=reports_kb("custom"))
        await save_master_home_message_id(master.id, sent.message_id)


async def show_reports(
    callback: CallbackQuery,
    state: FSMContext,
    period: str,
    custom_from: date = None,
    custom_to: date = None
) -> None:
    """Show reports for a period."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    today = date.today()

    if period == "today":
        date_from = today
        date_to = today
        period_text = "Сегодня"
    elif period == "week":
        date_from = today - timedelta(days=6)  # today - 6 days = 7 days total
        date_to = today
        period_text = "Неделя"
    elif period == "custom" and custom_from and custom_to:
        date_from = custom_from
        date_to = custom_to
        # Format: 01.03 — 31.03.2026
        if date_from.year == date_to.year:
            period_text = f"{date_from.strftime('%d.%m')} — {date_to.strftime('%d.%m.%Y')}"
        else:
            period_text = f"{date_from.strftime('%d.%m.%Y')} — {date_to.strftime('%d.%m.%Y')}"
    else:  # month
        date_from = today.replace(day=1)
        date_to = today
        period_text = f"{MONTHS_RU_NOM[today.month]} {today.year}"

    await state.update_data(current_screen="reports")

    data = await get_reports(master.id, date_from, date_to)

    # Build top services text (by popularity - count only)
    top_services_text = ""
    if data["top_services"] and data["order_count"] > 0:
        lines = []
        for s in data["top_services"]:
            cnt = s["count"]
            if cnt == 1:
                times_word = "раз"
            elif 2 <= cnt <= 4:
                times_word = "раза"
            else:
                times_word = "раз"
            lines.append(f"- {s['name']} — {cnt} {times_word}")
        top_services_text = "\n".join(lines)

    # Build top orders text (by amount)
    top_orders_text = ""
    if data.get("top_orders") and data["order_count"] > 0:
        lines = []
        for o in data["top_orders"]:
            order_date = datetime.fromisoformat(o["date"]).strftime("%d.%m")
            lines.append(f"- {o['amount']:,} ₽ — {o['client_name']} ({order_date})".replace(",", " "))
        top_orders_text = "\n".join(lines)

    # Build the report text
    if data["order_count"] == 0:
        text = (
            f"📊 Отчёты — {period_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"За этот период заказов нет.\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Выручка: 0 ₽\n"
            f"🛒 Заказов выполнено: 0\n"
            f"👥 Новых клиентов: {data['new_clients']}\n"
            f"🔄 Повторных клиентов: 0\n"
            f"🧾 Средний чек: 0 ₽\n"
            f"📋 Всего клиентов в базе: {data['total_clients']}\n"
            f"━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            f"📊 Отчёты — {period_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Выручка: {data['revenue']:,} ₽\n"
            f"🛒 Заказов выполнено: {data['order_count']}\n"
            f"👥 Новых клиентов: {data['new_clients']}\n"
            f"🔄 Повторных клиентов: {data['repeat_clients']}\n"
            f"🧾 Средний чек: {data['avg_check']:,} ₽\n"
            f"📋 Всего клиентов в базе: {data['total_clients']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🏆 Топ услуг по популярности:\n"
            f"{top_services_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Топ заказов по сумме:\n"
            f"{top_orders_text}\n"
            f"━━━━━━━━━━━━━━━"
        ).replace(",", " ")

    await edit_home_message(callback, text, reports_kb(period))
    await callback.answer()


# =============================================================================
# Settings Section
# =============================================================================

@router.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery, state: FSMContext) -> None:
    """Show settings section."""
    await state.update_data(current_screen="settings")

    text = (
        "⚙️ Настройки\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:profile")
async def cb_settings_profile(callback: CallbackQuery) -> None:
    """Show profile settings."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    tz_display = get_timezone_display(master.timezone)

    text = (
        "👤 Профиль\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {master.name or 'не указано'}\n"
        f"Сфера: {master.sphere or 'не указано'}\n"
        f"Контакты: {master.contacts or 'не указано'}\n"
        f"Соцсети: {master.socials or 'не указано'}\n"
        f"Режим работы: {master.work_hours or 'не указано'}\n"
        f"Часовой пояс: {tz_display}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_profile_kb())
    await callback.answer()


@router.callback_query(F.data == "profile:timezone")
async def cb_profile_timezone(callback: CallbackQuery) -> None:
    """Show timezone selection."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    tz_display = get_timezone_display(master.timezone)

    text = (
        "🕐 Часовой пояс\n"
        "━━━━━━━━━━━━━━━\n"
        f"Текущий: {tz_display}\n"
        "━━━━━━━━━━━━━━━\n"
        "Выберите ваш часовой пояс:"
    )

    await edit_home_message(callback, text, timezone_kb("settings:profile"))
    await callback.answer()


@router.callback_query(F.data.startswith("set_timezone:"))
async def cb_set_timezone(callback: CallbackQuery) -> None:
    """Set master timezone."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    tz_code = callback.data.split(":")[1]
    tz_display = get_timezone_display(tz_code)

    await update_master_bonus_setting(master.id, "timezone", tz_code)

    await callback.answer(f"✅ Часовой пояс: {tz_display}")

    # Return to profile
    master = await get_master_by_tg_id(tg_id)
    new_tz_display = get_timezone_display(master.timezone)

    text = (
        "👤 Профиль\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {master.name or 'не указано'}\n"
        f"Сфера: {master.sphere or 'не указано'}\n"
        f"Контакты: {master.contacts or 'не указано'}\n"
        f"Соцсети: {master.socials or 'не указано'}\n"
        f"Режим работы: {master.work_hours or 'не указано'}\n"
        f"Часовой пояс: {new_tz_display}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_profile_kb())


# =============================================================================
# Profile Edit FSM
# =============================================================================

PROFILE_FIELDS = {
    "name": ("Имя", "name"),
    "sphere": ("Сфера деятельности", "sphere"),
    "contacts": ("Контакты", "contacts"),
    "socials": ("Соцсети", "socials"),
    "work_hours": ("Режим работы", "work_hours"),
}


@router.callback_query(F.data.startswith("profile:edit:"))
async def cb_profile_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing a profile field."""
    field = callback.data.split(":")[2]

    if field not in PROFILE_FIELDS:
        await callback.answer("Неизвестное поле")
        return

    field_name, db_field = PROFILE_FIELDS[field]
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    current_value = getattr(master, db_field) or "не указано"

    await state.update_data(profile_edit_field=db_field)

    text = (
        f"✏️ Изменить: {field_name}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Текущее значение: {current_value}\n"
        f"━━━━━━━━━━━━━━━\n"
        "Введите новое значение:"
    )

    await edit_home_message(callback, text, stub_kb("settings:profile"))
    await state.set_state(ProfileEdit.waiting_value)
    await callback.answer()


@router.message(ProfileEdit.waiting_value)
async def profile_edit_value(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save new profile field value."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    db_field = data.get("profile_edit_field")

    value = message.text.strip()[:500]

    try:
        await message.delete()
    except:
        pass

    await update_master(master.id, **{db_field: value})
    await state.clear()

    # Refresh master data and show updated profile
    master = await get_master_by_tg_id(tg_id)

    text = (
        "👤 Профиль\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {master.name or 'не указано'}\n"
        f"Сфера: {master.sphere or 'не указано'}\n"
        f"Контакты: {master.contacts or 'не указано'}\n"
        f"Соцсети: {master.socials or 'не указано'}\n"
        f"Режим работы: {master.work_hours or 'не указано'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_profile_kb()
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data == "profile:gc")
async def cb_profile_gc(callback: CallbackQuery) -> None:
    """Show Google Calendar settings."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    # Check if connected
    email = await google_calendar.get_calendar_account(master.id)

    if email:
        text = (
            "📅 Google Calendar\n"
            "━━━━━━━━━━━━━━━\n"
            f"Статус: ✅ Подключён\n"
            f"Аккаунт: {email}"
        )
        kb = gc_connected_kb()
    else:
        text = (
            "📅 Google Calendar\n"
            "━━━━━━━━━━━━━━━\n"
            "Статус: ❌ Не подключён\n\n"
            "Подключите свой Google Calendar —\n"
            "заказы будут автоматически появляться\n"
            "в вашем расписании."
        )
        kb = gc_not_connected_kb()

    await edit_home_message(callback, text, kb)
    await callback.answer()


@router.callback_query(F.data == "gc:connect")
async def cb_gc_connect(callback: CallbackQuery) -> None:
    """Generate OAuth URL and send to master."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    url = await google_calendar.get_oauth_url(master.id)

    text = (
        "🔗 Для подключения Google Calendar:\n\n"
        f"1. Перейдите по ссылке:\n{url}\n\n"
        "2. Авторизуйтесь в Google\n"
        "3. Разрешите доступ к календарю\n\n"
        "После авторизации бот получит\n"
        "уведомление автоматически."
    )

    await edit_home_message(callback, text, gc_not_connected_kb())
    await callback.answer()


@router.callback_query(F.data == "gc:disconnect")
async def cb_gc_disconnect(callback: CallbackQuery) -> None:
    """Confirm Google Calendar disconnect."""
    text = (
        "❌ Отключить Google Calendar?\n\n"
        "Новые заказы больше не будут\n"
        "добавляться в календарь."
    )

    await edit_home_message(callback, text, gc_disconnect_confirm_kb())
    await callback.answer()


@router.callback_query(F.data == "gc:disconnect:confirm")
async def cb_gc_disconnect_confirm(callback: CallbackQuery) -> None:
    """Disconnect Google Calendar."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    await google_calendar.disconnect_calendar(master.id)

    text = (
        "📅 Google Calendar\n"
        "━━━━━━━━━━━━━━━\n"
        "Статус: ❌ Не подключён\n\n"
        "Google Calendar отключён.\n"
        "Вы можете подключить его снова."
    )

    await edit_home_message(callback, text, gc_not_connected_kb())
    await callback.answer("Отключено")


# =============================================================================
# Bonus Program Settings
# =============================================================================

@router.callback_query(F.data == "settings:bonus")
async def cb_settings_bonus(callback: CallbackQuery) -> None:
    """Show bonus program settings."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    status = "✅ Включена" if master.bonus_enabled else "❌ Выключена"

    welcome_str = f"{master.bonus_welcome} ₽" if master.bonus_welcome > 0 else "выкл"

    text = (
        "🎁 Бонусная программа\n"
        "━━━━━━━━━━━━━━━\n"
        f"Статус: {status}\n"
        f"Начисление: {master.bonus_rate}% от суммы заказа\n"
        f"Макс. списание: {master.bonus_max_spend}% суммы заказа\n"
        "━━━━━━━━━━━━━━━\n"
        f"🎉 Приветственный: {welcome_str}\n"
        f"🎂 Бонус на ДР: {master.bonus_birthday} ₽\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_bonus_kb(master.bonus_enabled))
    await callback.answer()


@router.callback_query(F.data == "bonus:toggle")
async def cb_bonus_toggle(callback: CallbackQuery) -> None:
    """Toggle bonus program on/off."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    new_value = not master.bonus_enabled
    await update_master(master.id, bonus_enabled=new_value)

    # Refresh and show updated screen
    master = await get_master_by_tg_id(tg_id)
    status = "✅ Включена" if master.bonus_enabled else "❌ Выключена"

    welcome_str = f"{master.bonus_welcome} ₽" if master.bonus_welcome > 0 else "выкл"

    text = (
        "🎁 Бонусная программа\n"
        "━━━━━━━━━━━━━━━\n"
        f"Статус: {status}\n"
        f"Начисление: {master.bonus_rate}% от суммы заказа\n"
        f"Макс. списание: {master.bonus_max_spend}% суммы заказа\n"
        "━━━━━━━━━━━━━━━\n"
        f"🎉 Приветственный: {welcome_str}\n"
        f"🎂 Бонус на ДР: {master.bonus_birthday} ₽\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_bonus_kb(master.bonus_enabled))
    await callback.answer("Настройка обновлена!")


BONUS_FIELDS = {
    "rate": ("% начисления", "bonus_rate", "Введите процент начисления (0-100):"),
    "max_spend": ("% списания", "bonus_max_spend", "Введите макс. процент списания (0-100):"),
    "birthday": ("Бонус на ДР", "bonus_birthday", "Введите сумму бонуса на день рождения:"),
}


@router.callback_query(F.data.startswith("bonus:edit:"))
async def cb_bonus_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing a bonus field."""
    field = callback.data.split(":")[2]

    if field not in BONUS_FIELDS:
        await callback.answer("Неизвестное поле")
        return

    field_name, db_field, prompt = BONUS_FIELDS[field]
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    current_value = getattr(master, db_field)

    await state.update_data(bonus_edit_field=db_field, bonus_field_type=field)

    text = (
        f"✏️ Изменить: {field_name}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Текущее значение: {current_value}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{prompt}"
    )

    await edit_home_message(callback, text, stub_kb("settings:bonus"))
    await state.set_state(BonusSettingsEdit.waiting_value)
    await callback.answer()


@router.message(BonusSettingsEdit.waiting_value)
async def bonus_edit_value(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save new bonus field value."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    db_field = data.get("bonus_edit_field")
    field_type = data.get("bonus_field_type")

    try:
        value = int(message.text.strip())
        if field_type in ("rate", "max_spend"):
            if value < 0 or value > 100:
                raise ValueError("Процент должен быть от 0 до 100")
        elif field_type == "birthday":
            if value < 0:
                raise ValueError("Сумма должна быть положительной")
    except ValueError as e:
        await message.answer(str(e) if str(e) else "Введите целое число")
        return

    try:
        await message.delete()
    except:
        pass

    await update_master(master.id, **{db_field: value})
    await state.clear()

    # Refresh and show updated screen
    master = await get_master_by_tg_id(tg_id)
    status = "✅ Включена" if master.bonus_enabled else "❌ Выключена"
    welcome_str = f"{master.bonus_welcome} ₽" if master.bonus_welcome > 0 else "выкл"

    text = (
        "🎁 Бонусная программа\n"
        "━━━━━━━━━━━━━━━\n"
        f"Статус: {status}\n"
        f"Начисление: {master.bonus_rate}% от суммы заказа\n"
        f"Макс. списание: {master.bonus_max_spend}% суммы заказа\n"
        "━━━━━━━━━━━━━━━\n"
        f"🎉 Приветственный: {welcome_str}\n"
        f"🎂 Бонус на ДР: {master.bonus_birthday} ₽\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_bonus_kb(master.bonus_enabled)
            )
        except TelegramBadRequest:
            pass


# =============================================================================
# Welcome & Birthday Bonus Message Settings
# =============================================================================

@router.callback_query(F.data == "bonus:welcome")
async def cb_bonus_welcome(callback: CallbackQuery) -> None:
    """Show welcome bonus settings."""
    await callback.answer()
    master = await get_master_by_tg_id(callback.from_user.id)

    amount_str = f"{master.bonus_welcome} ₽" if master.bonus_welcome > 0 else "выкл"
    text_str = "свой" if master.welcome_message else "стандартный"
    photo_str = "есть" if master.welcome_photo_id else "нет"

    text = (
        "🎉 Приветственный бонус\n"
        "━━━━━━━━━━━━━━━\n"
        f"Сумма: {amount_str}\n"
        f"Текст: {text_str}\n"
        f"Картинка: {photo_str}\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, bonus_message_kb("welcome"))


@router.callback_query(F.data == "bonus:birthday")
async def cb_bonus_birthday(callback: CallbackQuery) -> None:
    """Show birthday bonus settings."""
    await callback.answer()
    master = await get_master_by_tg_id(callback.from_user.id)

    text_str = "свой" if master.birthday_message else "стандартный"
    photo_str = "есть" if master.birthday_photo_id else "нет"

    text = (
        "🎂 Бонус на день рождения\n"
        "━━━━━━━━━━━━━━━\n"
        f"Сумма: {master.bonus_birthday} ₽\n"
        f"Текст: {text_str}\n"
        f"Картинка: {photo_str}\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, bonus_message_kb("birthday"))


@router.callback_query(F.data.regexp(r"^bonus:(welcome|birthday):amount$"))
async def cb_bonus_message_amount(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for bonus amount."""
    await callback.answer()
    bonus_type = callback.data.split(":")[1]

    await state.update_data(bonus_type=bonus_type)
    await state.set_state(BonusMessageEdit.waiting_amount)

    text = "💰 Введите сумму бонуса (0 = выключить):"
    await edit_home_message(callback, text, stub_kb(f"bonus:{bonus_type}"))


@router.callback_query(F.data.regexp(r"^bonus:(welcome|birthday):text$"))
async def cb_bonus_message_text(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for custom message text."""
    await callback.answer()
    bonus_type = callback.data.split(":")[1]

    await state.update_data(bonus_type=bonus_type)
    await state.set_state(BonusMessageEdit.waiting_text)

    variables = "{имя}, {мастер}, {бонус}" + (", {баланс}" if bonus_type == "birthday" else "")
    text = (
        f"✏️ Введите текст сообщения.\n\n"
        f"Переменные: {variables}\n\n"
        f"Отправьте «сброс» для возврата к стандартному."
    )
    await edit_home_message(callback, text, stub_kb(f"bonus:{bonus_type}"))


@router.callback_query(F.data.regexp(r"^bonus:(welcome|birthday):photo$"))
async def cb_bonus_message_photo(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for photo upload."""
    await callback.answer()
    bonus_type = callback.data.split(":")[1]

    await state.update_data(bonus_type=bonus_type)
    await state.set_state(BonusMessageEdit.waiting_photo)

    text = "🖼 Отправьте картинку или «удалить» для удаления."
    await edit_home_message(callback, text, stub_kb(f"bonus:{bonus_type}"))


@router.callback_query(F.data.regexp(r"^bonus:(welcome|birthday):preview$"))
async def cb_bonus_message_preview(callback: CallbackQuery, bot: Bot) -> None:
    """Send preview of bonus message."""
    await callback.answer("Отправляю предпросмотр...")
    bonus_type = callback.data.split(":")[1]
    master = await get_master_by_tg_id(callback.from_user.id)

    if bonus_type == "welcome":
        template = master.welcome_message
        default = DEFAULT_WELCOME_MESSAGE
        amount = master.bonus_welcome
        photo_id = master.welcome_photo_id
        balance = 0
    else:
        template = master.birthday_message
        default = DEFAULT_BIRTHDAY_MESSAGE
        amount = master.bonus_birthday
        photo_id = master.birthday_photo_id
        balance = 1500

    text = render_bonus_message(
        template=template,
        default=default,
        client_name="Анна",
        master_name=master.name,
        bonus_amount=amount,
        balance=balance,
    )

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Вернуться", callback_data=f"bonus:{bonus_type}:back")]
    ])

    try:
        if photo_id:
            await bot.send_photo(callback.from_user.id, photo_id, caption=text, reply_markup=back_kb)
        else:
            await bot.send_message(callback.from_user.id, text, reply_markup=back_kb)
    except Exception as e:
        await bot.send_message(callback.from_user.id, f"❌ Ошибка: {e}")


@router.callback_query(F.data.regexp(r"^bonus:(welcome|birthday):back$"))
async def cb_bonus_message_back(callback: CallbackQuery, bot: Bot) -> None:
    """Return from preview to bonus menu - delete preview message."""
    bonus_type = callback.data.split(":")[1]

    # Delete the preview message
    try:
        await callback.message.delete()
    except:
        pass

    # Show bonus submenu in home message
    master = await get_master_by_tg_id(callback.from_user.id)

    if bonus_type == "welcome":
        amount_str = f"{master.bonus_welcome} ₽" if master.bonus_welcome > 0 else "выкл"
        text_str = "свой" if master.welcome_message else "стандартный"
        photo_str = "есть" if master.welcome_photo_id else "нет"
        text = (
            "🎉 Приветственный бонус\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {amount_str}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )
    else:
        text_str = "свой" if master.birthday_message else "стандартный"
        photo_str = "есть" if master.birthday_photo_id else "нет"
        text = (
            "🎂 Бонус на день рождения\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {master.bonus_birthday} ₽\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )

    # Edit home message
    if master.home_message_id:
        try:
            await bot.edit_message_text(
                text,
                chat_id=callback.from_user.id,
                message_id=master.home_message_id,
                reply_markup=bonus_message_kb(bonus_type)
            )
        except:
            pass

    await callback.answer()


@router.message(BonusMessageEdit.waiting_amount)
async def on_bonus_message_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save bonus amount."""
    import asyncio
    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    bonus_type = data.get("bonus_type")
    master = await get_master_by_tg_id(message.from_user.id)

    try:
        amount = int(message.text.strip())
        if amount < 0:
            raise ValueError()
    except ValueError:
        error_msg = await bot.send_message(message.chat.id, "❌ Введите число >= 0")
        await asyncio.sleep(2)
        try:
            await error_msg.delete()
        except:
            pass
        return

    field = "bonus_welcome" if bonus_type == "welcome" else "bonus_birthday"
    await update_master_bonus_setting(master.id, field, amount)
    await state.clear()

    # Return to bonus submenu
    master = await get_master_by_tg_id(message.from_user.id)

    if bonus_type == "welcome":
        amount_str = f"{master.bonus_welcome} ₽" if master.bonus_welcome > 0 else "выкл"
        text_str = "свой" if master.welcome_message else "стандартный"
        photo_str = "есть" if master.welcome_photo_id else "нет"
        text = (
            "🎉 Приветственный бонус\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {amount_str}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )
    else:
        text_str = "свой" if master.birthday_message else "стандартный"
        photo_str = "есть" if master.birthday_photo_id else "нет"
        text = (
            "🎂 Бонус на день рождения\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {master.bonus_birthday} ₽\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=bonus_message_kb(bonus_type)
            )
        except TelegramBadRequest:
            pass


@router.message(BonusMessageEdit.waiting_text)
async def on_bonus_message_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save custom message text."""
    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    bonus_type = data.get("bonus_type")
    master = await get_master_by_tg_id(message.from_user.id)

    text_input = message.text.strip()
    value = None if text_input.lower() == "сброс" else text_input

    field = "welcome_message" if bonus_type == "welcome" else "birthday_message"
    await update_master_bonus_setting(master.id, field, value)
    await state.clear()

    # Return to bonus submenu
    master = await get_master_by_tg_id(message.from_user.id)

    if bonus_type == "welcome":
        amount_str = f"{master.bonus_welcome} ₽" if master.bonus_welcome > 0 else "выкл"
        text_str = "свой" if master.welcome_message else "стандартный"
        photo_str = "есть" if master.welcome_photo_id else "нет"
        text = (
            "🎉 Приветственный бонус\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {amount_str}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )
    else:
        text_str = "свой" if master.birthday_message else "стандартный"
        photo_str = "есть" if master.birthday_photo_id else "нет"
        text = (
            "🎂 Бонус на день рождения\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {master.bonus_birthday} ₽\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=bonus_message_kb(bonus_type)
            )
        except TelegramBadRequest:
            pass


@router.message(BonusMessageEdit.waiting_photo, F.photo)
async def on_bonus_message_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    """Save photo file_id."""
    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    bonus_type = data.get("bonus_type")
    master = await get_master_by_tg_id(message.from_user.id)

    photo_id = message.photo[-1].file_id

    field = "welcome_photo_id" if bonus_type == "welcome" else "birthday_photo_id"
    await update_master_bonus_setting(master.id, field, photo_id)
    await state.clear()

    # Return to bonus submenu
    master = await get_master_by_tg_id(message.from_user.id)

    if bonus_type == "welcome":
        amount_str = f"{master.bonus_welcome} ₽" if master.bonus_welcome > 0 else "выкл"
        text_str = "свой" if master.welcome_message else "стандартный"
        photo_str = "есть" if master.welcome_photo_id else "нет"
        text = (
            "🎉 Приветственный бонус\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {amount_str}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )
    else:
        text_str = "свой" if master.birthday_message else "стандартный"
        photo_str = "есть" if master.birthday_photo_id else "нет"
        text = (
            "🎂 Бонус на день рождения\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {master.bonus_birthday} ₽\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=bonus_message_kb(bonus_type)
            )
        except TelegramBadRequest:
            pass


@router.message(BonusMessageEdit.waiting_photo)
async def on_bonus_message_photo_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle text in photo state (for 'удалить')."""
    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    bonus_type = data.get("bonus_type")
    master = await get_master_by_tg_id(message.from_user.id)

    if message.text and message.text.strip().lower() == "удалить":
        field = "welcome_photo_id" if bonus_type == "welcome" else "birthday_photo_id"
        await update_master_bonus_setting(master.id, field, None)

    await state.clear()

    # Return to bonus submenu
    master = await get_master_by_tg_id(message.from_user.id)

    if bonus_type == "welcome":
        amount_str = f"{master.bonus_welcome} ₽" if master.bonus_welcome > 0 else "выкл"
        text_str = "свой" if master.welcome_message else "стандартный"
        photo_str = "есть" if master.welcome_photo_id else "нет"
        text = (
            "🎉 Приветственный бонус\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {amount_str}\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )
    else:
        text_str = "свой" if master.birthday_message else "стандартный"
        photo_str = "есть" if master.birthday_photo_id else "нет"
        text = (
            "🎂 Бонус на день рождения\n"
            "━━━━━━━━━━━━━━━\n"
            f"Сумма: {master.bonus_birthday} ₽\n"
            f"Текст: {text_str}\n"
            f"Картинка: {photo_str}\n"
            "━━━━━━━━━━━━━━━"
        )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=bonus_message_kb(bonus_type)
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data == "settings:services")
async def cb_settings_services(callback: CallbackQuery) -> None:
    """Show services catalog."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} ₽"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        "🛠 Справочник услуг\n"
        "━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_services_kb(services))
    await callback.answer()


# =============================================================================
# Services Management FSM
# =============================================================================

@router.callback_query(F.data == "settings:services:new")
async def cb_services_new(callback: CallbackQuery, state: FSMContext) -> None:
    """Start adding new service."""
    text = (
        "🛠 Новая услуга — Шаг 1/3\n"
        "━━━━━━━━━━━━━━━\n"
        "Введите название услуги:"
    )
    await edit_home_message(callback, text, stub_kb("settings:services"))
    await state.set_state(ServiceAdd.name)
    await callback.answer()


@router.message(ServiceAdd.name)
async def service_add_name(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 1: Service name."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    name = message.text.strip()[:200]
    await state.update_data(service_name=name)

    try:
        await message.delete()
    except:
        pass

    text = (
        "🛠 Новая услуга — Шаг 2/3\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {name}\n"
        "━━━━━━━━━━━━━━━\n"
        "💰 Введите цену (число) или нажмите «Без цены»:"
    )

    from src.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    no_price_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Без цены", callback_data="service:no_price")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="settings:services"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=no_price_kb
            )
        except TelegramBadRequest:
            pass

    await state.set_state(ServiceAdd.price)


@router.callback_query(ServiceAdd.price, F.data == "service:no_price")
async def service_add_no_price(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 2: No price - go to description."""
    await state.update_data(service_price=None)

    data = await state.get_data()
    name = data.get("service_name")

    text = (
        "🛠 Новая услуга — Шаг 3/3\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {name}\n"
        f"Цена: —\n"
        "━━━━━━━━━━━━━━━\n"
        "📝 Введите описание услуги или нажмите «Пропустить»:"
    )

    from src.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    skip_desc_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="service:skip_description")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="settings:services"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])

    await edit_home_message(callback, text, skip_desc_kb)
    await state.set_state(ServiceAdd.description)
    await callback.answer()


@router.message(ServiceAdd.price)
async def service_add_price(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 2: Service price - go to description."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        price = int(message.text.strip())
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("Введите положительное число")
        return

    try:
        await message.delete()
    except:
        pass

    await state.update_data(service_price=price)

    data = await state.get_data()
    name = data.get("service_name")

    text = (
        "🛠 Новая услуга — Шаг 3/3\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {name}\n"
        f"Цена: {price} ₽\n"
        "━━━━━━━━━━━━━━━\n"
        "📝 Введите описание услуги или нажмите «Пропустить»:"
    )

    from src.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    skip_desc_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="service:skip_description")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="settings:services"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=skip_desc_kb
            )
        except TelegramBadRequest:
            pass

    await state.set_state(ServiceAdd.description)


@router.callback_query(ServiceAdd.description, F.data == "service:skip_description")
async def service_add_skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Skip description - save service."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    name = data.get("service_name")
    price = data.get("service_price")

    await create_service(master.id, name, price, None)
    await state.clear()

    # Show updated services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} ₽"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Услуга «{name}» добавлена!\n"
        "━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_services_kb(services))
    await callback.answer("Услуга добавлена!")


@router.message(ServiceAdd.description)
async def service_add_description(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 3: Service description - save service."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    description = message.text.strip()[:500]

    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    name = data.get("service_name")
    price = data.get("service_price")

    await create_service(master.id, name, price, description)
    await state.clear()

    # Show updated services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} ₽"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Услуга «{name}» добавлена!\n"
        "━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_services_kb(services)
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.regexp(r"^settings:services:edit:\d+$"))
async def cb_services_edit(callback: CallbackQuery) -> None:
    """Show service edit menu."""
    service_id = int(callback.data.split(":")[3])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    description_line = f"📝 {service.description}\n" if service.description else ""
    text = (
        f"🛠 {service.name}\n"
        f"💰 {service.price or '—'} ₽\n"
        f"{description_line}"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, service_edit_kb(service_id))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^settings:services:edit:name:\d+$"))
async def cb_services_edit_name(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing service name."""
    service_id = int(callback.data.split(":")[4])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    await state.update_data(edit_service_id=service_id)

    text = (
        f"✏️ Изменить название\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Текущее: {service.name}\n"
        f"━━━━━━━━━━━━━━━\n"
        "Введите новое название:"
    )

    await edit_home_message(callback, text, stub_kb(f"settings:services:edit:{service_id}"))
    await state.set_state(ServiceEdit.name)
    await callback.answer()


@router.message(ServiceEdit.name)
async def service_edit_name(message: Message, state: FSMContext, bot: Bot) -> None:
    """Update service name."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    name = message.text.strip()[:200]

    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    service_id = data.get("edit_service_id")

    await update_service(service_id, name=name)
    await state.clear()

    # Show services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} ₽"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Название обновлено!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛠 Справочник услуг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_services_kb(services)
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.regexp(r"^settings:services:edit:price:\d+$"))
async def cb_services_edit_price(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing service price."""
    service_id = int(callback.data.split(":")[4])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    await state.update_data(edit_service_id=service_id)

    text = (
        f"💰 Изменить цену\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Текущая: {service.price or '—'} ₽\n"
        f"━━━━━━━━━━━━━━━\n"
        "Введите новую цену (число):"
    )

    from src.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    price_edit_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Убрать цену", callback_data=f"service:remove_price:{service_id}")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"settings:services:edit:{service_id}"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])

    await edit_home_message(callback, text, price_edit_kb)
    await state.set_state(ServiceEdit.price)
    await callback.answer()


@router.callback_query(ServiceEdit.price, F.data.startswith("service:remove_price:"))
async def service_remove_price(callback: CallbackQuery, state: FSMContext) -> None:
    """Remove service price."""
    service_id = int(callback.data.split(":")[2])

    await update_service(service_id, price=None)
    await state.clear()

    # Show services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} ₽"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Цена убрана!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛠 Справочник услуг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_services_kb(services))
    await callback.answer("Цена убрана!")


@router.message(ServiceEdit.price)
async def service_edit_price(message: Message, state: FSMContext, bot: Bot) -> None:
    """Update service price."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        price = int(message.text.strip())
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("Введите положительное число")
        return

    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    service_id = data.get("edit_service_id")

    await update_service(service_id, price=price)
    await state.clear()

    # Show services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} ₽"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Цена обновлена!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛠 Справочник услуг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_services_kb(services)
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.regexp(r"^settings:services:edit:description:\d+$"))
async def cb_services_edit_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing service description."""
    service_id = int(callback.data.split(":")[4])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    await state.update_data(edit_service_id=service_id)

    current_desc = service.description or "—"
    text = (
        f"📝 Изменить описание\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Текущее: {current_desc}\n"
        f"━━━━━━━━━━━━━━━\n"
        "Введите новое описание:"
    )

    from src.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    desc_edit_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Убрать описание", callback_data=f"service:remove_description:{service_id}")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"settings:services:edit:{service_id}"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])

    await edit_home_message(callback, text, desc_edit_kb)
    await state.set_state(ServiceEdit.description)
    await callback.answer()


@router.callback_query(ServiceEdit.description, F.data.startswith("service:remove_description:"))
async def service_remove_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Remove service description."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    service_id = int(callback.data.split(":")[2])

    await update_service(service_id, description=None)
    await state.clear()

    # Show services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} ₽"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Описание убрано!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛠 Справочник услуг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_services_kb(services))
    await callback.answer("Описание убрано!")


@router.message(ServiceEdit.description)
async def service_edit_description(message: Message, state: FSMContext, bot: Bot) -> None:
    """Update service description."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    description = message.text.strip()[:500]

    try:
        await message.delete()
    except:
        pass

    data = await state.get_data()
    service_id = data.get("edit_service_id")

    await update_service(service_id, description=description)
    await state.clear()

    # Show services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} ₽"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"✅ Описание обновлено!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛠 Справочник услуг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=settings_services_kb(services)
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.regexp(r"^settings:services:archive:\d+$"))
async def cb_services_archive(callback: CallbackQuery) -> None:
    """Archive a service."""
    service_id = int(callback.data.split(":")[3])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    await archive_service(service_id)

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    # Show updated services list
    services = await get_services(master.id)

    if services:
        services_text = "\n".join(
            f"• {s.name} — {s.price or '—'} ₽"
            for s in services
        )
    else:
        services_text = "Услуги не добавлены"

    text = (
        f"📦 Услуга «{service.name}» в архиве\n"
        "━━━━━━━━━━━━━━━\n"
        f"{services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_services_kb(services))
    await callback.answer("Услуга в архиве")


@router.callback_query(F.data == "settings:services:archive")
async def cb_services_show_archive(callback: CallbackQuery) -> None:
    """Show archived services."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    services = await get_archived_services(master.id)

    text = (
        "📦 Архив услуг\n"
        "━━━━━━━━━━━━━━━\n"
        "Нажмите на услугу, чтобы восстановить:"
    )

    await edit_home_message(callback, text, service_archived_kb(services))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^settings:services:restore:\d+$"))
async def cb_services_restore(callback: CallbackQuery) -> None:
    """Restore archived service."""
    service_id = int(callback.data.split(":")[3])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    await restore_service(service_id)

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    # Show updated archive
    services = await get_archived_services(master.id)

    text = (
        f"✅ Услуга «{service.name}» восстановлена!\n"
        "━━━━━━━━━━━━━━━\n"
        "📦 Архив услуг:"
    )

    await edit_home_message(callback, text, service_archived_kb(services))
    await callback.answer("Услуга восстановлена!")


@router.callback_query(F.data == "settings:invite")
async def cb_settings_invite(callback: CallbackQuery) -> None:
    """Show invite link."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    invite_link = f"t.me/{CLIENT_BOT_USERNAME}?start={master.invite_token}"

    text = (
        "🔗 Ссылка для клиентов\n"
        "━━━━━━━━━━━━━━━\n"
        f"{invite_link}\n\n"
        "Отправьте эту ссылку клиентам или\n"
        "разместите в соцсетях.\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_invite_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:invite:qr")
async def cb_settings_invite_qr(callback: CallbackQuery) -> None:
    """QR code stub."""
    text = "🚧 QR-код — в разработке"
    await edit_home_message(callback, text, stub_kb("settings:invite"))
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
    from src.oauth_server import run_oauth_server, set_master_bot

    await init_db()
    logger.info("Database initialized")

    bot = Bot(token=MASTER_BOT_TOKEN)
    dp = setup_dispatcher()

    # Set bot instance for OAuth server notifications
    set_master_bot(bot)

    logger.info("Starting master bot...")

    # Run bot polling and OAuth server concurrently
    await asyncio.gather(
        dp.start_polling(bot),
        run_oauth_server(),
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
