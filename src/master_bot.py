"""Master bot - for service providers to manage clients, orders, and marketing."""

import logging
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

from src.config import MASTER_BOT_TOKEN, CLIENT_BOT_USERNAME, LOG_LEVEL
from src.states import MasterRegistration
from src.keyboards import (
    home_master_kb, orders_kb, order_card_kb, calendar_kb,
    clients_kb, client_card_kb, client_history_kb, client_bonus_kb,
    marketing_kb, reports_kb, settings_kb, settings_profile_kb,
    settings_bonus_kb, settings_services_kb, settings_invite_kb,
    skip_kb, stub_kb,
)
from src.database import (
    init_db,
    get_master_by_tg_id,
    get_master_by_id,
    create_master,
    update_master,
    save_master_home_message_id,
    get_orders_today,
    get_orders_by_date,
    get_order_by_id,
    get_active_dates,
    search_clients,
    get_client_with_stats,
    get_client_orders,
    get_client_bonus_log,
    get_services,
    get_reports,
)
from src.utils import generate_invite_token

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
        orders_text = "\n".join(
            f"• {o.get('scheduled_at', '')[:5] if o.get('scheduled_at') else '—'} — "
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


async def show_home(bot: Bot, master, chat_id: int, message_id: int = None) -> int:
    """Show or update home screen. Returns message_id."""
    text = await build_home_text(master)
    keyboard = home_master_kb()

    if message_id and master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=keyboard
            )
            return master.home_message_id
        except TelegramBadRequest:
            pass

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
        await show_home(bot, master, message.chat.id)
        return

    # Start registration
    await message.answer(
        "👋 Добро пожаловать в Master CRM Bot!\n\n"
        "Давайте настроим ваш профиль.\n\n"
        "📝 Введите ваше имя или псевдоним:"
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
        "📞 Введите контакты для клиентов:\n"
        "(телефон, мессенджеры, email)",
        reply_markup=skip_kb()
    )
    await state.set_state(MasterRegistration.contacts)


@router.callback_query(MasterRegistration.sphere, F.data == "skip")
async def reg_sphere_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 2: Skip sphere."""
    await state.update_data(sphere=None)
    await callback.message.edit_text(
        "📞 Введите контакты для клиентов:\n"
        "(телефон, мессенджеры, email)"
    )
    await callback.message.answer("Или пропустите:", reply_markup=skip_kb())
    await state.set_state(MasterRegistration.contacts)
    await callback.answer()


@router.message(MasterRegistration.contacts)
async def reg_contacts(message: Message, state: FSMContext) -> None:
    """Step 3: Save contacts."""
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
    orders = await get_orders_today(master.id)

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

    text = (
        f"📋 Заказ #{order['id']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {order.get('client_name', '—')}\n"
        f"📞 {order.get('client_phone', '—')}\n"
        f"📍 {order.get('address', '—')}\n"
        f"🕐 {time_str} | {date_str}\n"
        f"🛠 {order.get('services', '—')}\n"
        f"💰 Итого: {order.get('amount_total', 0) or '—'} ₽\n"
        f"📊 Статус: {status_map.get(order.get('status', ''), order.get('status', ''))}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, order_card_kb(order_id, order.get("status", "")))
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

    orders = await get_orders_by_date(master.id, selected_date)

    day = selected_date.day
    month = MONTHS_RU[selected_date.month]

    text = (
        f"📦 Заказы — {day} {month}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await state.update_data(orders_date=date_str)
    await edit_home_message(callback, text, orders_kb(orders, selected_date))
    await callback.answer()


@router.callback_query(F.data == "orders:new")
async def cb_orders_new(callback: CallbackQuery) -> None:
    """New order stub."""
    text = "🚧 Создание заказа — в разработке"
    await edit_home_message(callback, text, stub_kb("orders"))
    await callback.answer()


@router.callback_query(F.data.startswith("orders:complete:"))
async def cb_orders_complete(callback: CallbackQuery) -> None:
    """Complete order stub."""
    text = "🚧 Провести заказ — в разработке"
    await edit_home_message(callback, text, stub_kb("orders"))
    await callback.answer()


@router.callback_query(F.data.startswith("orders:move:"))
async def cb_orders_move(callback: CallbackQuery) -> None:
    """Move order stub."""
    text = "🚧 Перенос заказа — в разработке"
    await edit_home_message(callback, text, stub_kb("orders"))
    await callback.answer()


@router.callback_query(F.data.startswith("orders:cancel:"))
async def cb_orders_cancel(callback: CallbackQuery) -> None:
    """Cancel order stub."""
    text = "🚧 Отмена заказа — в разработке"
    await edit_home_message(callback, text, stub_kb("orders"))
    await callback.answer()


# =============================================================================
# Clients Section
# =============================================================================

@router.callback_query(F.data == "clients")
async def cb_clients(callback: CallbackQuery, state: FSMContext) -> None:
    """Show clients section."""
    await state.update_data(current_screen="clients")

    text = (
        "👥 Клиенты\n"
        "━━━━━━━━━━━━━━━\n"
        "🔍 Введите имя или телефон для поиска:"
    )

    await edit_home_message(callback, text, clients_kb())
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


@router.callback_query(F.data.startswith("clients:history:"))
async def cb_client_history(callback: CallbackQuery, state: FSMContext) -> None:
    """View client history."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    client_id = int(callback.data.split(":")[2])
    client = await get_client_with_stats(master.id, client_id)
    orders = await get_client_orders(master.id, client_id)

    if orders:
        orders_text = "\n".join(
            f"• {o.get('scheduled_at', '')[:10] if o.get('scheduled_at') else '—'} — "
            f"{o.get('services', '—')[:30]} | {o.get('amount_total', 0)} ₽"
            for o in orders
        )
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
    """View client bonus log."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    client_id = int(callback.data.split(":")[2])
    client = await get_client_with_stats(master.id, client_id)
    bonus_log = await get_client_bonus_log(master.id, client_id)

    if bonus_log:
        log_text = "\n".join(
            f"• {b.get('created_at', '')[:10] if b.get('created_at') else '—'} "
            f"{'+' if b.get('amount', 0) > 0 else ''}{b.get('amount', 0)} — {b.get('comment', '—')}"
            for b in bonus_log
        )
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


@router.callback_query(F.data == "clients:new")
async def cb_clients_new(callback: CallbackQuery) -> None:
    """New client stub."""
    text = "🚧 Добавление клиента — в разработке"
    await edit_home_message(callback, text, stub_kb("clients"))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:edit:"))
async def cb_clients_edit(callback: CallbackQuery) -> None:
    """Edit client stub."""
    client_id = callback.data.split(":")[2]
    text = "🚧 Редактирование клиента — в разработке"
    await edit_home_message(callback, text, stub_kb(f"clients:view:{client_id}"))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:note:"))
async def cb_clients_note(callback: CallbackQuery) -> None:
    """Edit client note stub."""
    client_id = callback.data.split(":")[2]
    text = "🚧 Заметка — в разработке"
    await edit_home_message(callback, text, stub_kb(f"clients:view:{client_id}"))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:bonus:add:"))
async def cb_clients_bonus_add(callback: CallbackQuery) -> None:
    """Add bonus stub."""
    client_id = callback.data.split(":")[3]
    text = "🚧 Начисление бонусов — в разработке"
    await edit_home_message(callback, text, stub_kb(f"clients:bonus:{client_id}"))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:bonus:sub:"))
async def cb_clients_bonus_sub(callback: CallbackQuery) -> None:
    """Subtract bonus stub."""
    client_id = callback.data.split(":")[3]
    text = "🚧 Списание бонусов — в разработке"
    await edit_home_message(callback, text, stub_kb(f"clients:bonus:{client_id}"))
    await callback.answer()


# Handle text search when on clients screen
@router.message(F.text)
async def handle_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle text input for search."""
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
    """Show marketing section."""
    await state.update_data(current_screen="marketing")

    text = (
        "📢 Маркетинг\n"
        "━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, marketing_kb())
    await callback.answer()


@router.callback_query(F.data == "marketing:broadcast")
async def cb_marketing_broadcast(callback: CallbackQuery) -> None:
    """Broadcast stub."""
    text = "🚧 Рассылка — в разработке"
    await edit_home_message(callback, text, stub_kb("marketing"))
    await callback.answer()


@router.callback_query(F.data == "marketing:promo")
async def cb_marketing_promo(callback: CallbackQuery) -> None:
    """Promo stub."""
    text = "🚧 Создание акции — в разработке"
    await edit_home_message(callback, text, stub_kb("marketing"))
    await callback.answer()


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
async def cb_reports_period(callback: CallbackQuery) -> None:
    """Custom period stub."""
    text = "🚧 Выбор периода — в разработке"
    await edit_home_message(callback, text, stub_kb("reports"))
    await callback.answer()


async def show_reports(callback: CallbackQuery, state: FSMContext, period: str) -> None:
    """Show reports for a period."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    today = date.today()

    if period == "today":
        date_from = today
        date_to = today
        period_text = "Сегодня"
    elif period == "week":
        date_from = today - timedelta(days=7)
        date_to = today
        period_text = "Неделя"
    else:  # month
        date_from = today.replace(day=1)
        date_to = today
        period_text = f"{MONTHS_RU_NOM[today.month]} {today.year}"

    await state.update_data(current_screen="reports")

    data = await get_reports(master.id, date_from, date_to)

    top_services_text = ""
    if data["top_services"]:
        top_services_text = "\n".join(
            f"• {s['name']} — {s['total']} ₽"
            for s in data["top_services"]
        )
    else:
        top_services_text = "Нет данных"

    text = (
        f"📊 Отчёты — {period_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 Выручка: {data['revenue']} ₽\n"
        f"🛒 Заказов: {data['order_count']}\n"
        f"👥 Новых клиентов: {data['new_clients']}\n"
        f"🔄 Повторных: {data['repeat_clients']}\n"
        f"🧾 Средний чек: {data['avg_check']} ₽\n"
        f"📋 Всего в базе: {data['total_clients']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Топ услуг:\n"
        f"{top_services_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

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

    text = (
        "👤 Профиль\n"
        "━━━━━━━━━━━━━━━\n"
        f"Имя: {master.name}\n"
        f"Сфера: {master.sphere or '—'}\n"
        f"Контакты: {master.contacts or '—'}\n"
        f"Соцсети: {master.socials or '—'}\n"
        f"Режим работы: {master.work_hours or '—'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_profile_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("settings:profile:"))
async def cb_settings_profile_field(callback: CallbackQuery) -> None:
    """Edit profile field stub."""
    text = "🚧 Редактирование профиля — в разработке"
    await edit_home_message(callback, text, stub_kb("settings:profile"))
    await callback.answer()


@router.callback_query(F.data == "settings:bonus")
async def cb_settings_bonus(callback: CallbackQuery) -> None:
    """Show bonus program settings."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    status = "✅ Включена" if master.bonus_enabled else "❌ Выключена"

    text = (
        "🎁 Бонусная программа\n"
        "━━━━━━━━━━━━━━━\n"
        f"Статус: {status}\n"
        f"Начисление: {master.bonus_rate}% от суммы заказа\n"
        f"Макс. списание: {master.bonus_max_spend}% суммы заказа\n"
        f"Бонус на ДР: {master.bonus_birthday} ₽\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, settings_bonus_kb(master.bonus_enabled))
    await callback.answer()


@router.callback_query(F.data.startswith("settings:bonus:"))
async def cb_settings_bonus_field(callback: CallbackQuery) -> None:
    """Edit bonus field stub."""
    text = "🚧 Настройка бонусной программы — в разработке"
    await edit_home_message(callback, text, stub_kb("settings:bonus"))
    await callback.answer()


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


@router.callback_query(F.data.startswith("settings:services:"))
async def cb_settings_services_action(callback: CallbackQuery) -> None:
    """Services action stub."""
    text = "🚧 Управление услугами — в разработке"
    await edit_home_message(callback, text, stub_kb("settings:services"))
    await callback.answer()


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
    dp.include_router(router)
    return dp


async def main() -> None:
    """Main entry point."""
    await init_db()
    logger.info("Database initialized")

    bot = Bot(token=MASTER_BOT_TOKEN)
    dp = setup_dispatcher()

    logger.info("Starting master bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
