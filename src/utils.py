"""Utility functions for Master CRM Bot."""

import re
import secrets
from datetime import date
from typing import Optional


def generate_invite_token() -> str:
    """Generate a cryptographically secure invite token."""
    return secrets.token_urlsafe(16)


def format_phone(phone: str) -> str:
    """Normalize phone number to +7XXXXXXXXXX format."""
    # Remove all non-digit characters
    digits = re.sub(r"\D", "", phone)

    # Handle different formats
    if len(digits) == 11:
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        elif digits.startswith("7"):
            pass
    elif len(digits) == 10:
        digits = "7" + digits

    return "+" + digits if digits else phone


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
