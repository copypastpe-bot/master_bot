"""Utility functions for Master CRM Bot."""

import re
import secrets
from datetime import date
from typing import Optional


def generate_invite_token() -> str:
    """Generate a cryptographically secure invite token."""
    return secrets.token_urlsafe(16)


def normalize_phone(phone: str) -> Optional[str]:
    """Normalize phone number to +79991234567 format.

    Returns normalized phone or None if invalid.

    Accepts formats:
    - +79991234567
    - 89991234567
    - 79991234567
    - 9991234567
    - +7 999 123-45-67
    - 8 (999) 123-45-67
    """
    if not phone:
        return None

    # Remove all non-digit characters
    digits = re.sub(r"\D", "", phone)

    # Handle different formats
    if len(digits) == 11:
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        elif digits.startswith("7"):
            pass
        else:
            return None  # Invalid 11-digit number
    elif len(digits) == 10:
        # Assume Russian number without country code
        digits = "7" + digits
    else:
        return None  # Invalid length

    # Validate: must be 11 digits starting with 7
    if len(digits) != 11 or not digits.startswith("7"):
        return None

    return "+" + digits


# Дефолтные тексты бонусных сообщений
DEFAULT_WELCOME_MESSAGE = """👋 Добро пожаловать, {имя}!

Ваш мастер {мастер} дарит вам приветственный бонус 🎁 {бонус} ₽

Используйте его при следующем заказе!"""

DEFAULT_BIRTHDAY_MESSAGE = """🎂 С днём рождения, {имя}!

Ваш мастер {мастер} дарит вам 🎁 {бонус} бонусов!

💰 Ваш баланс: {баланс} ₽

Используйте бонусы при следующем заказе."""


def render_bonus_message(
    template: Optional[str],
    default: str,
    client_name: str,
    master_name: str,
    bonus_amount: int,
    balance: int = 0,
) -> str:
    """Render bonus message with variable substitution."""
    text = template if template else default
    return text.format(
        имя=client_name,
        мастер=master_name,
        бонус=bonus_amount,
        баланс=balance,
    )


# Часовые пояса для выбора
TIMEZONES = [
    ("Europe/Kaliningrad", "Калининград", "UTC+2"),
    ("Europe/Moscow", "Москва", "UTC+3"),
    ("Europe/Samara", "Самара", "UTC+4"),
    ("Asia/Yekaterinburg", "Екатеринбург", "UTC+5"),
    ("Asia/Novosibirsk", "Новосибирск", "UTC+7"),
    ("Asia/Vladivostok", "Владивосток", "UTC+10"),
]


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
