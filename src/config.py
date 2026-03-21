"""Configuration module - loads environment variables from .env file."""

import os
from dotenv import load_dotenv

load_dotenv()

# Bot tokens
MASTER_BOT_TOKEN: str = os.getenv("MASTER_BOT_TOKEN", "")
CLIENT_BOT_TOKEN: str = os.getenv("CLIENT_BOT_TOKEN", "")
CLIENT_BOT_USERNAME: str = os.getenv("CLIENT_BOT_USERNAME", "")

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
MINIAPP_URL: str = os.getenv("MINIAPP_URL", "https://app.crmfit.ru")
