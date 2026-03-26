"""Client handlers: list, add, edit, notes, bonuses."""

from datetime import date

from aiogram import Bot, Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from src.database import (
    get_master_by_tg_id,
    search_clients,
    get_client_with_stats,
    get_client_by_id,
    get_client_orders_history,
    get_client_bonus_log,
    get_clients_paginated,
    create_client,
    link_client_to_master,
    update_client,
    update_client_note,
    manual_bonus_transaction,
    get_last_client_address,
    archive_client,
    restore_client,
    get_archived_clients,
)
from src.keyboards import (
    clients_kb,
    clients_paginated_kb,
    client_card_kb,
    client_history_kb,
    client_bonus_kb,
    client_edit_kb,
    order_address_kb,
    stub_kb,
    skip_kb,
    client_archive_confirm_kb,
    archived_clients_kb,
)
from src.states import ClientAdd, ClientEdit, ClientNote, BonusManual, CreateOrder
from src.utils import normalize_phone, get_currency_symbol
from src.handlers.common import edit_home_message, MONTHS_RU

router = Router(name="clients")

ORDER_STATUS_ICONS = {
    "new": "🆕",
    "confirmed": "📌",
    "done": "✅",
    "cancelled": "❌",
    "moved": "📅",
}


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


@router.callback_query(F.data == "clients:archive")
async def cb_clients_archive_list(callback: CallbackQuery) -> None:
    """Show archived clients list."""
    master = await get_master_by_tg_id(callback.from_user.id)
    clients = await get_archived_clients(master.id)
    hint = "\nНажмите ↩️ чтобы восстановить клиента." if clients else ""
    text = (
        "📦 Архив клиентов\n"
        "━━━━━━━━━━━━━━━\n"
        f"Архивировано: {len(clients)}"
        + hint
    )
    await edit_home_message(callback, text, archived_clients_kb(clients))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:archive:confirm:"))
async def cb_client_archive_confirm(callback: CallbackQuery) -> None:
    """Show archive confirmation screen."""
    client_id = int(callback.data.split(":")[3])
    master = await get_master_by_tg_id(callback.from_user.id)
    client = await get_client_with_stats(master.id, client_id)

    name = client["name"] if client else "Клиент"
    text = (
        f"📦 Архивировать клиента?\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {name}\n\n"
        "Клиент исчезнет из основного списка.\n"
        "Вы сможете восстановить его из раздела Архив."
    )
    await edit_home_message(callback, text, client_archive_confirm_kb(client_id))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:archive:do:"))
async def cb_client_archive_do(callback: CallbackQuery) -> None:
    """Archive the client."""
    client_id = int(callback.data.split(":")[3])
    master = await get_master_by_tg_id(callback.from_user.id)
    client = await get_client_with_stats(master.id, client_id)
    if not client:
        await callback.answer("Клиент не найден")
        return
    await archive_client(master.id, client_id)

    clients, total = await get_clients_paginated(master.id, page=1)
    total_pages = max(1, (total + 9) // 10)
    text = (
        "👥 Клиенты\n"
        "━━━━━━━━━━━━━━━\n"
        "✅ Клиент перемещён в архив.\n\n"
        "🔍 Введите часть имени/телефона\n"
        "для поиска или выберите из списка.\n"
        f"стр 1 из {total_pages}"
    )
    await edit_home_message(callback, text, clients_paginated_kb(clients, 1, total))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:restore:"))
async def cb_client_restore(callback: CallbackQuery) -> None:
    """Restore archived client."""
    client_id = int(callback.data.split(":")[2])
    master = await get_master_by_tg_id(callback.from_user.id)
    await restore_client(master.id, client_id)

    clients = await get_archived_clients(master.id)
    hint = "\n\nНажмите ↩️ чтобы восстановить клиента." if clients else ""
    text = (
        "📦 Архив клиентов\n"
        "━━━━━━━━━━━━━━━\n"
        f"✅ Клиент восстановлен.\n\n"
        f"Архивировано: {len(clients)}"
        + hint
    )
    await edit_home_message(callback, text, archived_clients_kb(clients))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:view:"))
async def cb_client_view(callback: CallbackQuery, state: FSMContext) -> None:
    """View client card."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

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
        except Exception:
            birthday_text = "не указана"
    else:
        birthday_text = "не указана"

    text = (
        f"👤 {client.get('name', '—')}\n"
        f"📞 {client.get('phone', '—')}\n"
        f"🎂 {birthday_text}\n"
        f"💰 Бонусов: {client.get('bonus_balance', 0)} {curr}\n"
        f"🛒 Заказов: {client.get('order_count', 0)} | Потрачено: {client.get('total_spent', 0)} {curr}\n"
        f"📝 {client.get('note') or '—'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await state.update_data(current_client_id=client_id)
    await edit_home_message(callback, text, client_card_kb(client_id))
    await callback.answer()


@router.callback_query(F.data.startswith("clients:history:"))
async def cb_client_history(callback: CallbackQuery, state: FSMContext) -> None:
    """View client history with status icons."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    curr = get_currency_symbol(master.currency)

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
            return f"{icon} {scheduled} — {services} | {amount} {curr}"

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
    curr = get_currency_symbol(master.currency)

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
        f"Баланс: {client.get('bonus_balance', 0)} {curr}\n"
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
    except TelegramBadRequest:
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
    except (ValueError, AttributeError):
        pass

    try:
        await message.delete()
    except TelegramBadRequest:
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
    except TelegramBadRequest:
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
        except (ValueError, AttributeError):
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
    curr = get_currency_symbol(master.currency)

    birthday_str = client.get("birthday", "")
    if birthday_str:
        try:
            bd = date.fromisoformat(birthday_str)
            birthday_text = f"{bd.day} {MONTHS_RU[bd.month]}"
        except Exception:
            birthday_text = "не указана"
    else:
        birthday_text = "не указана"

    text = (
        f"✅ Сохранено!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {client.get('name', '—')}\n"
        f"📞 {client.get('phone', '—')}\n"
        f"🎂 {birthday_text}\n"
        f"💰 Бонусов: {client.get('bonus_balance', 0)} {curr}\n"
        f"🛒 Заказов: {client.get('order_count', 0)} | Потрачено: {client.get('total_spent', 0)} {curr}\n"
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
    except TelegramBadRequest:
        pass

    # Delete note if "-"
    if note_text == "-":
        note_text = None

    # Update note
    await update_client_note(master.id, client_id, note_text)

    await state.clear()

    # Show updated client card
    client = await get_client_with_stats(master.id, client_id)
    curr = get_currency_symbol(master.currency)

    birthday_str = client.get("birthday", "")
    if birthday_str:
        try:
            bd = date.fromisoformat(birthday_str)
            birthday_text = f"{bd.day} {MONTHS_RU[bd.month]}"
        except Exception:
            birthday_text = "не указана"
    else:
        birthday_text = "не указана"

    text = (
        f"✅ Заметка сохранена!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {client.get('name', '—')}\n"
        f"📞 {client.get('phone', '—')}\n"
        f"🎂 {birthday_text}\n"
        f"💰 Бонусов: {client.get('bonus_balance', 0)} {curr}\n"
        f"🛒 Заказов: {client.get('order_count', 0)} | Потрачено: {client.get('total_spent', 0)} {curr}\n"
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

    curr = get_currency_symbol(master.currency)
    await state.update_data(
        bonus_client_id=client_id,
        bonus_operation="add"
    )

    text = (
        f"➕ Начисление бонусов — {client.get('name', 'Клиент')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Баланс: {client.get('bonus_balance', 0)} {curr}\n"
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

    curr = get_currency_symbol(master.currency)
    await state.update_data(
        bonus_client_id=client_id,
        bonus_operation="sub"
    )

    text = (
        f"➖ Списание бонусов — {client.get('name', 'Клиент')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Баланс: {client.get('bonus_balance', 0)} {curr}\n"
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
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    client_id = data.get("bonus_client_id")
    operation = data.get("bonus_operation")

    await state.update_data(bonus_amount=amount)

    client = await get_client_with_stats(master.id, client_id)
    curr = get_currency_symbol(master.currency)
    op_text = "начисления" if operation == "add" else "списания"
    sign = "+" if operation == "add" else "-"

    text = (
        f"💬 Комментарий к {op_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Сумма: {sign}{amount} {curr}\n"
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
    except TelegramBadRequest:
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
    curr = get_currency_symbol(master.currency)

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
        f"🎁 Баланс: {new_balance} {curr}\n"
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
        except TelegramBadRequest:
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
