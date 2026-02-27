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
