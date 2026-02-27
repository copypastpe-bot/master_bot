"""Inline keyboards for Master CRM Bot."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def master_home_kb() -> InlineKeyboardMarkup:
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


def client_home_kb() -> InlineKeyboardMarkup:
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
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications"),
        ],
    ])


def skip_kb() -> InlineKeyboardMarkup:
    """Skip button keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip"),
        ],
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
