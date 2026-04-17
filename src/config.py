"""Configuration module - loads environment variables from .env file."""

import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from dotenv import load_dotenv

load_dotenv()

# Bot tokens
MASTER_BOT_TOKEN: str = os.getenv("MASTER_BOT_TOKEN", "")
CLIENT_BOT_TOKEN: str = os.getenv("CLIENT_BOT_TOKEN", "")
CLIENT_BOT_USERNAME: str = os.getenv("CLIENT_BOT_USERNAME", "")
MASTER_BOT_USERNAME: str = os.getenv("MASTER_BOT_USERNAME", "")

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Google OAuth
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")
OAUTH_SERVER_PORT: int = int(os.getenv("OAUTH_SERVER_PORT", "8090"))

# Mini App API
API_PORT: int = int(os.getenv("API_PORT", "8081"))
def _append_query_param(url: str, key: str, value: str) -> str:
    """Return URL with an extra query parameter, preserving existing params."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[key] = value
    return urlunsplit(parts._replace(query=urlencode(query)))


MINIAPP_URL: str = os.getenv("MINIAPP_URL", "https://app.crmfit.ru")
CLIENT_MINIAPP_URL: str = os.getenv(
    "CLIENT_MINIAPP_URL",
    _append_query_param(MINIAPP_URL, "app", "client"),
)

# Environment (development / production)
APP_ENV: str = os.getenv("APP_ENV", "production")

# Subscription & referrals
SUBSCRIPTION_PLANS: dict[str, dict[str, int | str]] = {
    "plan_month": {"stars": 200, "days": 30, "label": "1 месяц"},
    "plan_quarter": {"stars": 500, "days": 90, "label": "3 месяца"},
    "plan_year": {"stars": 1700, "days": 365, "label": "1 год"},
}
TRIAL_DAYS: int = 7
REFERRAL_BONUS_DAYS: int = 14
REFERRAL_EXTRA_DAYS: int = 14
REMINDER_DAYS_BEFORE: int = 3
