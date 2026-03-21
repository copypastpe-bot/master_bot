"""Order handlers: list, create, complete, move, cancel."""

import logging
from datetime import datetime, date

from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from src.database import (
    get_master_by_tg_id,
    get_orders_today,
    get_orders_by_date,
    get_order_by_id,
    get_active_dates,
    search_clients,
    get_client_by_id,
    get_services,
    create_client,
    link_client_to_master,
    get_master_client,
    create_order,
    create_order_items,
    update_order_status,
    update_order_schedule,
    get_last_client_address,
    apply_bonus_transaction,
    save_gc_event_id,
    mark_order_confirmed_by_client,
    reset_order_for_reconfirmation,
)
from src.keyboards import (
    home_master_kb,
    orders_kb,
    order_card_kb,
    calendar_kb,
    client_search_results_kb,
    order_address_kb,
    order_calendar_kb,
    order_hour_kb,
    order_minutes_kb,
    order_services_kb,
    order_confirm_kb,
    order_edit_field_kb,
    complete_amount_kb,
    payment_type_kb,
    bonus_use_kb,
    complete_confirm_kb,
    move_confirm_kb,
    move_hour_kb,
    move_minutes_kb,
    cancel_reason_kb,
    cancel_confirm_kb,
    stub_kb,
    skip_kb,
)
from src.states import CreateOrder, CreateClientInOrder, CompleteOrder, MoveOrder, CancelOrder
from src.utils import normalize_phone, get_currency_symbol
from src.handlers.common import edit_home_message, build_home_text, MONTHS_RU
from src import notifications
from src import google_calendar

logger = logging.getLogger(__name__)
router = Router(name="orders")


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
    curr = get_currency_symbol(master.currency)

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
        f"💰 Итого: {order.get('amount_total', 0) or '—'} {curr}\n"
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
    except TelegramBadRequest:
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
    except TelegramBadRequest:
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
    except TelegramBadRequest:
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
        except TelegramBadRequest:
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
    except (ValueError, AttributeError):
        pass

    try:
        await message.delete()
    except TelegramBadRequest:
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
    except TelegramBadRequest:
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
    curr = get_currency_symbol(master.currency)

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

    await edit_home_message(callback, text, order_services_kb(services_list, [], [], curr))
    await state.set_state(CreateOrder.services)
    await callback.answer()


@router.callback_query(CreateOrder.services, F.data.startswith("order:service:"))
async def order_select_service(callback: CallbackQuery, state: FSMContext) -> None:
    """Select or toggle a service."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

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

    await edit_home_message(callback, text, order_services_kb(services_list, selected, custom_services, curr))
    await callback.answer()


@router.message(CreateOrder.custom_service)
async def order_enter_custom_service(message: Message, state: FSMContext, bot: Bot) -> None:
    """Enter custom service name."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    custom_name = message.text.strip()[:200]

    try:
        await message.delete()
    except TelegramBadRequest:
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
                reply_markup=order_services_kb(services_list, selected, custom_services, curr)
            )
        except TelegramBadRequest:
            pass

    await state.set_state(CreateOrder.services)


@router.callback_query(CreateOrder.services, F.data == "order:services:done")
async def order_services_done(callback: CallbackQuery, state: FSMContext) -> None:
    """Finish services selection, go to amount."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

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
        f"💰 Введите сумму{' (предлагаем ' + str(suggested_amount) + ' ' + curr + ')' if suggested_amount else ''}:"
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
    except TelegramBadRequest:
        pass

    await state.update_data(order_amount=amount)
    curr = get_currency_symbol(master.currency)

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
        f"💰 Сумма: {amount} {curr}\n"
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
    curr = get_currency_symbol(master.currency)

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
            scheduled_at=scheduled_at,
            currency=curr
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
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

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
        f"💰 Сумма: {amount} {curr}\n"
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
        curr = get_currency_symbol(master.currency)
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
        await edit_home_message(callback, text, order_services_kb(services_list, selected, custom_services, curr))
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

    curr = get_currency_symbol(master.currency)
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
        f"💰 Сумма: {amount} {curr}\n"
        "Подтвердите или измените:"
    )

    await edit_home_message(callback, text, complete_amount_kb(amount, curr))
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
    except TelegramBadRequest:
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
    curr = get_currency_symbol(master.currency)

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
                    f"💰 Сумма: {amount} {curr}\n"
                    "━━━━━━━━━━━━━━━\n"
                    "🎁 Списать бонусы?"
                )

                await edit_home_message(callback, text, bonus_use_kb(mc.bonus_balance, max_can_use, curr))
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
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

    data = await state.get_data()
    max_bonus = data.get("complete_max_bonus", 0)

    text = (
        "✅ Провести заказ\n"
        "━━━━━━━━━━━━━━━\n"
        f"🎁 Введите сумму бонусов (макс. {max_bonus} {curr}):"
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
    curr = get_currency_symbol(master.currency)

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
    except TelegramBadRequest:
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
        f"💰 Сумма: {amount} {curr}\n"
        f"🎁 Списано бонусов: {bonus} {curr}\n"
        f"💵 К оплате: {final_amount} {curr}\n"
        f"💳 Оплата: {payment_names.get(payment_type, payment_type)}\n"
        f"⭐ Будет начислено: +{bonus_accrued} {curr}\n"
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
    curr = get_currency_symbol(master.currency)

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
        f"💰 Сумма: {amount} {curr}\n"
    )

    if bonus_spent > 0:
        text += f"🎁 Списано бонусов: {bonus_spent} {curr}\n"
        text += f"💵 К оплате: {final_amount} {curr}\n"

    text += f"💳 Оплата: {payment_names.get(payment_type, payment_type)}\n"

    if master.bonus_enabled:
        text += f"⭐ Будет начислено: +{bonus_accrued} {curr}\n"

    text += "━━━━━━━━━━━━━━━"

    await edit_home_message(callback, text, complete_confirm_kb())
    await state.set_state(CompleteOrder.confirm)


@router.callback_query(CompleteOrder.confirm, F.data == "complete:confirm:yes")
async def complete_order_final(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Complete the order."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

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
        f"💰 Сумма: {amount} {curr}\n"
    )
    if bonus_spent > 0:
        text += f"🎁 Списано: {bonus_spent} {curr}\n"
    if bonus_accrued > 0:
        text += f"⭐ Начислено: +{bonus_accrued} {curr}\n"
    text += f"📊 Статус: ✅ выполнен\n"
    text += "━━━━━━━━━━━━━━━"

    await edit_home_message(callback, text, order_card_kb(order_id, updated_order.get("client_id"), "done"))
    await callback.answer("Заказ выполнен!")


@router.callback_query(F.data == "complete:cancel")
async def complete_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel order completion - return to order card."""
    data = await state.get_data()
    order_id = data.get("complete_order_id")

    await state.clear()

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

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
        f"💰 Итого: {order.get('amount_total', 0) or '—'} {curr}\n"
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
    curr = get_currency_symbol(master.currency)

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
        f"💰 Итого: {updated_order.get('amount_total', 0) or '—'} {curr}\n"
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
    curr = get_currency_symbol(master.currency)

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
        f"💰 Итого: {order.get('amount_total', 0) or '—'} {curr}\n"
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
    except TelegramBadRequest:
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
