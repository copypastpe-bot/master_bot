"""Telegram Mini App initData validation."""

import hmac
import hashlib
import json
from typing import Optional
from urllib.parse import parse_qsl, unquote


def validate_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """
    Validate Telegram initData signature.
    Returns parsed data dict or None if signature is invalid.
    """
    vals = dict(parse_qsl(unquote(init_data), keep_blank_values=True))
    received_hash = vals.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(vals.items())
    )

    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()

    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        return None

    return vals


def extract_tg_id(validated_data: dict) -> Optional[int]:
    """Extract Telegram user ID from validated initData."""
    user_str = validated_data.get("user")
    if not user_str:
        return None
    try:
        user = json.loads(user_str)
        return user.get("id")
    except (json.JSONDecodeError, TypeError):
        return None
