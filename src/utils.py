"""Utility functions for Master CRM Bot."""

import re
import secrets
from datetime import date
from typing import Optional


def generate_invite_token() -> str:
    """Generate a cryptographically secure invite token."""
    return secrets.token_urlsafe(16)


def normalize_phone(phone: str, default_region: str = "RU") -> Optional[str]:
    """Normalize phone number to E.164 format (+XXXXXXXXXXX).

    Returns normalized phone or None if invalid.

    Supports international formats:
    - +79991234567 (Russia)
    - 89991234567 (Russia with 8)
    - +995591234567 (Georgia)
    - +380501234567 (Ukraine)
    - +1234567890 (any country)
    - And any format with spaces, dashes, parentheses
    """
    if not phone:
        return None

    try:
        import phonenumbers

        # Try to parse with default region
        parsed = phonenumbers.parse(phone, default_region)

        # Validate the number
        if not phonenumbers.is_valid_number(parsed):
            return None

        # Return in E.164 format (+XXXXXXXXXXX)
        return phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.E164
        )
    except Exception:
        return None


# Дефолтные тексты бонусных сообщений
DEFAULT_WELCOME_MESSAGE = """👋 Добро пожаловать, {имя}!

Ваш мастер {мастер} дарит вам приветственный бонус 🎁 {бонус} {валюта}

Используйте его при следующем заказе!"""

DEFAULT_BIRTHDAY_MESSAGE = """🎂 С днём рождения, {имя}!

Ваш мастер {мастер} дарит вам 🎁 {бонус} бонусов!

💰 Ваш баланс: {баланс} {валюта}

Используйте бонусы при следующем заказе."""


def render_bonus_message(
    template: Optional[str],
    default: str,
    client_name: str,
    master_name: str,
    bonus_amount: int,
    balance: int = 0,
    currency: str = "₽",
    welcome_bonus: Optional[int] = None,
    birthday_bonus: Optional[int] = None,
) -> str:
    """Render bonus message with variable substitution."""
    text = template if template else default
    inv_bonus = bonus_amount if welcome_bonus is None else welcome_bonus
    bd_bonus = bonus_amount if birthday_bonus is None else birthday_bonus

    replacements = {
        "{имя}": str(client_name),
        "{мастер}": str(master_name),
        "{бонус}": str(bonus_amount),
        "{баланс}": str(balance),
        "{валюта}": str(currency),
        "{name}": str(client_name),
        "{master}": str(master_name),
        "{bonus}": str(bonus_amount),
        "{balance}": str(balance),
        "{currency}": str(currency),
        "{inv_bonus}": str(inv_bonus),
        "{bd_bonus}": str(bd_bonus),
    }

    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


DEFAULT_FEEDBACK_MESSAGE = (
    "Спасибо, что обратились к {master_name}!\n"
    "Как прошёл визит? Оцените от 1 до 5:"
)

DEFAULT_FEEDBACK_REPLY_5 = "Спасибо за высокую оценку! Будем рады видеть вас снова 🙏"


def render_feedback_message(template: Optional[str], default: str, master_name: str, services: str) -> str:
    """Render feedback message template with variable substitution."""
    text = template if template else default
    replacements = {
        "{master_name}": str(master_name),
        "{мастер}": str(master_name),
        "{service}": str(services),
        "{услуга}": str(services),
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


# Часовые пояса для выбора
TIMEZONES = [
    ("Europe/Kaliningrad", "Калининград", "UTC+2"),
    ("Europe/Moscow", "Москва", "UTC+3"),
    ("Europe/Samara", "Самара", "UTC+4"),
    ("Asia/Yekaterinburg", "Екатеринбург", "UTC+5"),
    ("Asia/Novosibirsk", "Новосибирск", "UTC+7"),
    ("Asia/Vladivostok", "Владивосток", "UTC+10"),
]

# Валюты
CURRENCIES = [
    ("RUB", "₽", "Рубль"),
    ("GEL", "₾", "Лари"),
    ("USD", "$", "Доллар"),
    ("EUR", "€", "Евро"),
    ("RSD", "дин.", "Динар"),
]


def get_currency_symbol(currency_code: str) -> str:
    """Get currency symbol by code."""
    for code, symbol, name in CURRENCIES:
        if code == currency_code:
            return symbol
    return "₽"


def get_currency_display(currency_code: str) -> str:
    """Get display name for currency code."""
    for code, symbol, name in CURRENCIES:
        if code == currency_code:
            return f"{symbol} {name}"
    return currency_code


def get_timezone_display(tz_code: str) -> str:
    """Get display name for timezone code."""
    for code, name, utc in TIMEZONES:
        if code == tz_code:
            return f"{name} ({utc})"
    return tz_code


def format_phone(phone: str) -> str:
    """Normalize phone number to +7XXXXXXXXXX format.

    Legacy function - use normalize_phone() for validation.
    """
    result = normalize_phone(phone)
    return result if result else phone


def parse_date(date_str: str) -> Optional[date]:
    """Parse birthday date from various formats.

    Supported formats:
    - DD.MM.YYYY
    - DD/MM/YYYY
    - DD-MM-YYYY
    - DD.MM (assumes current year)
    - DD/MM (assumes current year)
    - DD-MM (assumes current year)
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Try different separators
    for sep in [".", "/", "-"]:
        if sep in date_str:
            parts = date_str.split(sep)
            try:
                day = int(parts[0])
                month = int(parts[1])
                year = int(parts[2]) if len(parts) > 2 else date.today().year

                # Handle 2-digit year
                if year < 100:
                    year += 2000 if year < 50 else 1900

                return date(year, month, day)
            except (ValueError, IndexError):
                continue

    return None
