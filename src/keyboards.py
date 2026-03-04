"""Inline keyboards for Master CRM Bot."""

import calendar
from datetime import date
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

MONTHS_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]


# =============================================================================
# Master Bot Keyboards
# =============================================================================

def home_master_kb() -> InlineKeyboardMarkup:
    """Main menu keyboard for master."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 Заказы", callback_data="orders"),
            InlineKeyboardButton(text="👥 Клиенты", callback_data="clients"),
        ],
        [
            InlineKeyboardButton(text="📢 Маркетинг", callback_data="marketing"),
            InlineKeyboardButton(text="📊 Отчёты", callback_data="reports"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
        ],
    ])


def orders_kb(orders: list, selected_date: date = None) -> InlineKeyboardMarkup:
    """Orders list keyboard."""
    buttons = []

    # Order buttons
    for order in orders:
        time_str = order.get("scheduled_at", "")[:5] if order.get("scheduled_at") else "—"
        client_name = order.get("client_name", "Клиент")
        services = order.get("services", "")[:20] if order.get("services") else ""
        text = f"{time_str} — {client_name}"
        if services:
            text += f" | {services}"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"orders:view:{order['id']}"
        )])

    if not orders:
        buttons.append([InlineKeyboardButton(text="📭 Заказов нет", callback_data="noop")])

    # Action buttons
    buttons.append([InlineKeyboardButton(text="+ Новый заказ", callback_data="orders:new")])
    buttons.append([
        InlineKeyboardButton(text="📅 Другой день", callback_data="orders:calendar"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_card_kb(order_id: int, status: str) -> InlineKeyboardMarkup:
    """Order card keyboard."""
    buttons = []

    if status in ("new", "confirmed"):
        buttons.append([
            InlineKeyboardButton(text="✅ Провести", callback_data=f"orders:complete:{order_id}"),
            InlineKeyboardButton(text="📅 Перенести", callback_data=f"orders:move:{order_id}"),
        ])
        buttons.append([
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"orders:cancel:{order_id}"),
        ])
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="orders"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def calendar_kb(year: int, month: int, active_dates: list[date]) -> InlineKeyboardMarkup:
    """Inline calendar keyboard."""
    buttons = []

    # Header with navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    buttons.append([
        InlineKeyboardButton(text="◀️", callback_data=f"orders:calendar:{prev_year}:{prev_month}"),
        InlineKeyboardButton(text=f"{MONTHS_RU[month]} {year}", callback_data="noop"),
        InlineKeyboardButton(text="▶️", callback_data=f"orders:calendar:{next_year}:{next_month}"),
    ])

    # Weekday headers
    buttons.append([
        InlineKeyboardButton(text=day, callback_data="noop")
        for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    ])

    # Days grid
    cal = calendar.Calendar(firstweekday=0)
    active_set = {d.day for d in active_dates}

    for week in cal.monthdayscalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
            else:
                day_text = f"[{day}]" if day in active_set else str(day)
                row.append(InlineKeyboardButton(
                    text=day_text,
                    callback_data=f"orders:calendar:date:{year}-{month:02d}-{day:02d}"
                ))
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="🏠 Главная", callback_data="home")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def clients_kb(results: list = None) -> InlineKeyboardMarkup:
    """Clients section keyboard."""
    buttons = []

    if results:
        for client in results:
            name = client.get("name", "Клиент")
            phone = client.get("phone", "")
            text = f"{name}"
            if phone:
                text += f" | {phone}"
            buttons.append([InlineKeyboardButton(
                text=text,
                callback_data=f"clients:view:{client['id']}"
            )])

    buttons.append([InlineKeyboardButton(text="+ Добавить клиента", callback_data="clients:new")])
    buttons.append([InlineKeyboardButton(text="🏠 Главная", callback_data="home")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def client_card_kb(client_id: int) -> InlineKeyboardMarkup:
    """Client card keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 История", callback_data=f"clients:history:{client_id}"),
            InlineKeyboardButton(text="🎁 Бонусы", callback_data=f"clients:bonus:{client_id}"),
        ],
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"clients:edit:{client_id}"),
            InlineKeyboardButton(text="📝 Заметка", callback_data=f"clients:note:{client_id}"),
        ],
        [InlineKeyboardButton(text="➕ Создать заказ", callback_data=f"clients:order:{client_id}")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="clients"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


def client_edit_kb(client_id: int) -> InlineKeyboardMarkup:
    """Client edit keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Имя", callback_data=f"clients:edit:name:{client_id}"),
            InlineKeyboardButton(text="✏️ Телефон", callback_data=f"clients:edit:phone:{client_id}"),
        ],
        [InlineKeyboardButton(text="✏️ Дата рождения", callback_data=f"clients:edit:birthday:{client_id}")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"clients:view:{client_id}"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


def client_history_kb(client_id: int) -> InlineKeyboardMarkup:
    """Client history keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"clients:view:{client_id}"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


def client_bonus_kb(client_id: int) -> InlineKeyboardMarkup:
    """Client bonus log keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Начислить", callback_data=f"clients:bonus:add:{client_id}"),
            InlineKeyboardButton(text="➖ Списать", callback_data=f"clients:bonus:sub:{client_id}"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"clients:view:{client_id}"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


def marketing_kb() -> InlineKeyboardMarkup:
    """Marketing section keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="marketing:broadcast")],
        [InlineKeyboardButton(text="🎁 Создать акцию", callback_data="marketing:promo")],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="home")],
    ])


def reports_kb(active: str = "month") -> InlineKeyboardMarkup:
    """Reports section keyboard."""
    def mark(period: str) -> str:
        return f"· {period}" if active == period.lower() else period

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=mark("Сегодня") if active == "today" else "Сегодня",
                               callback_data="reports:today"),
            InlineKeyboardButton(text=mark("Неделя") if active == "week" else "Неделя",
                               callback_data="reports:week"),
        ],
        [
            InlineKeyboardButton(text=mark("Месяц") if active == "month" else "Месяц",
                               callback_data="reports:month"),
            InlineKeyboardButton(text="📅 Период", callback_data="reports:period"),
        ],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="home")],
    ])


def settings_kb() -> InlineKeyboardMarkup:
    """Settings section keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="settings:profile")],
        [InlineKeyboardButton(text="🎁 Бонусная программа", callback_data="settings:bonus")],
        [InlineKeyboardButton(text="🛠 Справочник услуг", callback_data="settings:services")],
        [InlineKeyboardButton(text="🔗 Инвайт-ссылка", callback_data="settings:invite")],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="home")],
    ])


def settings_profile_kb() -> InlineKeyboardMarkup:
    """Profile settings keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Имя", callback_data="profile:edit:name"),
            InlineKeyboardButton(text="✏️ Сфера", callback_data="profile:edit:sphere"),
        ],
        [
            InlineKeyboardButton(text="✏️ Контакты", callback_data="profile:edit:contacts"),
            InlineKeyboardButton(text="✏️ Соцсети", callback_data="profile:edit:socials"),
        ],
        [InlineKeyboardButton(text="✏️ Режим работы", callback_data="profile:edit:work_hours")],
        [InlineKeyboardButton(text="📅 Google Calendar", callback_data="profile:gc")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="settings"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


def settings_bonus_kb(bonus_enabled: bool) -> InlineKeyboardMarkup:
    """Bonus program settings keyboard."""
    toggle_text = "🔄 Выключить" if bonus_enabled else "🔄 Включить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data="bonus:toggle")],
        [
            InlineKeyboardButton(text="✏️ % начисления", callback_data="bonus:edit:rate"),
            InlineKeyboardButton(text="✏️ % списания", callback_data="bonus:edit:max_spend"),
        ],
        [InlineKeyboardButton(text="✏️ Бонус на ДР", callback_data="bonus:edit:birthday")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="settings"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


def settings_services_kb(services: list, show_archive_btn: bool = True) -> InlineKeyboardMarkup:
    """Services catalog keyboard."""
    buttons = []

    for service in services:
        price_str = f"{service.price} ₽" if service.price else "—"
        buttons.append([InlineKeyboardButton(
            text=f"{service.name} — {price_str} ✏️",
            callback_data=f"settings:services:edit:{service.id}"
        )])

    buttons.append([InlineKeyboardButton(text="+ Добавить услугу", callback_data="settings:services:new")])
    if show_archive_btn:
        buttons.append([InlineKeyboardButton(text="📦 Показать архив", callback_data="settings:services:archive")])
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="settings"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_edit_kb(service_id: int) -> InlineKeyboardMarkup:
    """Service edit keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"settings:services:edit:name:{service_id}")],
        [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"settings:services:edit:price:{service_id}")],
        [InlineKeyboardButton(text="📦 В архив", callback_data=f"settings:services:archive:{service_id}")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="settings:services"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


def service_archived_kb(services: list) -> InlineKeyboardMarkup:
    """Archived services keyboard."""
    buttons = []

    for service in services:
        price_str = f"{service.price} ₽" if service.price else "—"
        buttons.append([InlineKeyboardButton(
            text=f"📦 {service.name} — {price_str}",
            callback_data=f"settings:services:restore:{service.id}"
        )])

    if not services:
        buttons.append([InlineKeyboardButton(text="Архив пуст", callback_data="noop")])

    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="settings:services"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_invite_kb() -> InlineKeyboardMarkup:
    """Invite link keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 QR-код", callback_data="settings:invite:qr")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="settings"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


# =============================================================================
# Client Bot Keyboards
# =============================================================================

def home_client_kb() -> InlineKeyboardMarkup:
    """Main menu keyboard for client."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Мои бонусы", callback_data="bonuses"),
            InlineKeyboardButton(text="📋 История", callback_data="history"),
        ],
        [
            InlineKeyboardButton(text="🎁 Акции", callback_data="promos"),
            InlineKeyboardButton(text="📞 Заказать", callback_data="order_request"),
        ],
        [
            InlineKeyboardButton(text="❓ Вопрос", callback_data="question"),
            InlineKeyboardButton(text="📸 Фото/видео", callback_data="media"),
        ],
        [
            InlineKeyboardButton(text="👨‍🔧 Мой мастер", callback_data="master_info"),
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications"),
        ],
    ])


def client_bonuses_kb() -> InlineKeyboardMarkup:
    """Client bonuses section keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главная", callback_data="home")],
    ])


def client_bot_history_kb() -> InlineKeyboardMarkup:
    """Client bot history section keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главная", callback_data="home")],
    ])


def client_promos_kb() -> InlineKeyboardMarkup:
    """Client promos section keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главная", callback_data="home")],
    ])


def client_master_info_kb() -> InlineKeyboardMarkup:
    """Client master info keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главная", callback_data="home")],
    ])


def client_notifications_kb(notify_24h: bool, notify_1h: bool, notify_marketing: bool, notify_promos: bool) -> InlineKeyboardMarkup:
    """Client notifications settings keyboard."""
    def status(enabled: bool) -> str:
        return "✅" if enabled else "❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Напоминание за 24ч: {status(notify_24h)}",
            callback_data="notifications:toggle:notify_24h"
        )],
        [InlineKeyboardButton(
            text=f"Напоминание за 1ч: {status(notify_1h)}",
            callback_data="notifications:toggle:notify_1h"
        )],
        [InlineKeyboardButton(
            text=f"Рассылки мастера: {status(notify_marketing)}",
            callback_data="notifications:toggle:notify_marketing"
        )],
        [InlineKeyboardButton(
            text=f"Акции: {status(notify_promos)}",
            callback_data="notifications:toggle:notify_promos"
        )],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="home")],
    ])


# =============================================================================
# Common Keyboards
# =============================================================================

def back_kb(callback: str) -> InlineKeyboardMarkup:
    """Single back button keyboard with home."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=callback),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


def stub_kb(back_callback: str) -> InlineKeyboardMarkup:
    """Stub keyboard with back and home buttons."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


def skip_kb() -> InlineKeyboardMarkup:
    """Skip button keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")],
    ])


def share_contact_kb() -> ReplyKeyboardMarkup:
    """Share contact button keyboard (Reply keyboard, not Inline)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# =============================================================================
# Order Creation Keyboards
# =============================================================================

def client_search_results_kb(clients: list) -> InlineKeyboardMarkup:
    """Client search results for order creation."""
    buttons = []

    for client in clients:
        name = client.get("name", "Клиент")
        phone = client.get("phone", "")
        text = f"{name}"
        if phone:
            text += f" | {phone}"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"order:client:{client['id']}"
        )])

    buttons.append([InlineKeyboardButton(
        text="+ Создать нового клиента",
        callback_data="order:client:new"
    )])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="order:cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_address_kb(last_address: str = None) -> InlineKeyboardMarkup:
    """Address selection keyboard."""
    buttons = []

    if last_address:
        buttons.append([InlineKeyboardButton(
            text=f"📍 {last_address[:40]}",
            callback_data="order:address:last"
        )])

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="order:cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_calendar_kb(year: int, month: int, prefix: str = "order") -> InlineKeyboardMarkup:
    """Calendar keyboard for order date selection."""
    buttons = []

    # Header with navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    buttons.append([
        InlineKeyboardButton(text="◀️", callback_data=f"{prefix}:cal:{prev_year}:{prev_month}"),
        InlineKeyboardButton(text=f"{MONTHS_RU[month]} {year}", callback_data="noop"),
        InlineKeyboardButton(text="▶️", callback_data=f"{prefix}:cal:{next_year}:{next_month}"),
    ])

    # Weekday headers
    buttons.append([
        InlineKeyboardButton(text=day, callback_data="noop")
        for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    ])

    # Days grid
    cal = calendar.Calendar(firstweekday=0)

    for week in cal.monthdayscalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton(
                    text=str(day),
                    callback_data=f"{prefix}:date:{year}-{month:02d}-{day:02d}"
                ))
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="order:cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_hour_kb() -> InlineKeyboardMarkup:
    """Hour selection keyboard (8-19)."""
    buttons = []

    # Hours in rows of 4
    hours = list(range(8, 20))  # 8-19
    for i in range(0, len(hours), 4):
        row = [
            InlineKeyboardButton(text=f"{h}:00", callback_data=f"order:hour:{h}")
            for h in hours[i:i+4]
        ]
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="order:cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_minutes_kb(hour: int) -> InlineKeyboardMarkup:
    """Minutes selection keyboard (00/30)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{hour}:00", callback_data="order:minutes:00"),
            InlineKeyboardButton(text=f"{hour}:30", callback_data="order:minutes:30"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="order:cancel")],
    ])


def order_services_kb(services: list, selected: list = None, custom_services: list = None) -> InlineKeyboardMarkup:
    """Services selection keyboard.

    Args:
        services: list of available services from catalog
        selected: list of selected service IDs
        custom_services: list of custom service names
    """
    buttons = []
    selected = selected or []
    custom_services = custom_services or []

    for service in services:
        is_selected = service["id"] in selected
        prefix = "✓ " if is_selected else ""
        price_str = f" — {service['price']} ₽" if service.get("price") else ""
        buttons.append([InlineKeyboardButton(
            text=f"{prefix}{service['name']}{price_str}",
            callback_data=f"order:service:{service['id']}"
        )])

    buttons.append([InlineKeyboardButton(
        text="✏️ Своя услуга",
        callback_data="order:service:custom"
    )])

    # Show "Готово" button as soon as ANY service is selected (catalog or custom)
    has_selections = len(selected) > 0 or len(custom_services) > 0
    if has_selections:
        buttons.append([InlineKeyboardButton(
            text="✅ Готово",
            callback_data="order:services:done"
        )])

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="order:cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_confirm_kb() -> InlineKeyboardMarkup:
    """Order confirmation keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Создать", callback_data="order:confirm:yes"),
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить", callback_data="order:edit"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="order:cancel"),
        ],
    ])


def order_edit_field_kb() -> InlineKeyboardMarkup:
    """Select which field to edit keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Клиент", callback_data="order:edit:client"),
            InlineKeyboardButton(text="📍 Адрес", callback_data="order:edit:address"),
        ],
        [
            InlineKeyboardButton(text="📅 Дата", callback_data="order:edit:date"),
            InlineKeyboardButton(text="⏰ Время", callback_data="order:edit:time"),
        ],
        [
            InlineKeyboardButton(text="🛠 Услуги", callback_data="order:edit:services"),
            InlineKeyboardButton(text="💰 Сумма", callback_data="order:edit:amount"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="order:back_to_confirm"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


# =============================================================================
# Order Completion Keyboards
# =============================================================================

def complete_amount_kb(amount: int) -> InlineKeyboardMarkup:
    """Amount confirmation keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"✅ Подтвердить {amount} ₽",
            callback_data="complete:amount:confirm"
        )],
        [InlineKeyboardButton(
            text="✏️ Изменить сумму",
            callback_data="complete:amount:change"
        )],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="complete:cancel")],
    ])


def payment_type_kb() -> InlineKeyboardMarkup:
    """Payment type selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 Наличные", callback_data="complete:pay:cash"),
            InlineKeyboardButton(text="💳 Карта", callback_data="complete:pay:card"),
        ],
        [
            InlineKeyboardButton(text="📱 Перевод", callback_data="complete:pay:transfer"),
            InlineKeyboardButton(text="📄 По счёту", callback_data="complete:pay:invoice"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="complete:cancel")],
    ])


def bonus_use_kb(bonus_balance: int, max_can_use: int) -> InlineKeyboardMarkup:
    """Bonus usage keyboard."""
    text = f"Списать до {max_can_use} ₽ (баланс: {bonus_balance} ₽)"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ {text}", callback_data="complete:bonus:yes")],
        [InlineKeyboardButton(text="❌ Не списывать", callback_data="complete:bonus:no")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="complete:cancel")],
    ])


def complete_confirm_kb() -> InlineKeyboardMarkup:
    """Order completion confirmation keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Провести", callback_data="complete:confirm:yes")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="complete:cancel")],
    ])


# =============================================================================
# Order Move/Reschedule Keyboards
# =============================================================================

def move_confirm_kb() -> InlineKeyboardMarkup:
    """Move order confirmation keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Перенести", callback_data="move:confirm:yes")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="move:cancel")],
    ])


def move_hour_kb() -> InlineKeyboardMarkup:
    """Hour selection keyboard for moving order."""
    buttons = []

    hours = list(range(8, 20))
    for i in range(0, len(hours), 4):
        row = [
            InlineKeyboardButton(text=f"{h}:00", callback_data=f"move:hour:{h}")
            for h in hours[i:i+4]
        ]
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="move:cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def move_minutes_kb(hour: int) -> InlineKeyboardMarkup:
    """Minutes selection keyboard for moving order."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{hour}:00", callback_data="move:minutes:00"),
            InlineKeyboardButton(text=f"{hour}:30", callback_data="move:minutes:30"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="move:cancel")],
    ])


# =============================================================================
# Order Cancel Keyboards
# =============================================================================

def cancel_reason_kb() -> InlineKeyboardMarkup:
    """Cancel reason selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Клиент отменил", callback_data="cancel:reason:client")],
        [InlineKeyboardButton(text="🔧 Мастер не может", callback_data="cancel:reason:master")],
        [InlineKeyboardButton(text="✏️ Своя причина", callback_data="cancel:reason:custom")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="cancel:reason:skip")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="cancel:back"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])


def cancel_confirm_kb() -> InlineKeyboardMarkup:
    """Cancel order confirmation keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить заказ", callback_data="cancel:confirm:yes")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="cancel:back"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="home"),
        ],
    ])
