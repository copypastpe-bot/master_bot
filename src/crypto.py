"""Encryption utilities for sensitive data protection."""

import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Get encryption key from environment
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

_fernet: Optional[Fernet] = None


def _get_fernet() -> Optional[Fernet]:
    """Get or create Fernet instance."""
    global _fernet
    if _fernet is None and ENCRYPTION_KEY:
        try:
            _fernet = Fernet(ENCRYPTION_KEY.encode())
        except Exception as e:
            logger.error(f"Failed to initialize Fernet: {e}")
            return None
    return _fernet


def encrypt(value: Optional[str]) -> Optional[str]:
    """Encrypt a string value. Returns None if value is None or encryption unavailable."""
    if value is None:
        return None

    fernet = _get_fernet()
    if fernet is None:
        # No encryption key configured - return plain text
        # This allows graceful degradation during development
        logger.warning("ENCRYPTION_KEY not set - storing data unencrypted")
        return value

    try:
        encrypted = fernet.encrypt(value.encode())
        # Prefix with 'enc:' to identify encrypted values
        return "enc:" + base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return value


def decrypt(value: Optional[str]) -> Optional[str]:
    """Decrypt a string value. Returns original if not encrypted or decryption fails."""
    if value is None:
        return None

    # Check if value is encrypted (has 'enc:' prefix)
    if not value.startswith("enc:"):
        # Not encrypted - return as is (for backward compatibility)
        return value

    fernet = _get_fernet()
    if fernet is None:
        logger.error("Cannot decrypt: ENCRYPTION_KEY not set")
        return None

    try:
        # Remove 'enc:' prefix and decode
        encrypted = base64.urlsafe_b64decode(value[4:].encode())
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode()
    except InvalidToken:
        logger.error("Decryption failed: invalid token (wrong key?)")
        return None
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return None


def is_encrypted(value: Optional[str]) -> bool:
    """Check if a value is encrypted."""
    return value is not None and value.startswith("enc:")


def generate_key() -> str:
    """Generate a new encryption key. Use this once to create ENCRYPTION_KEY."""
    return Fernet.generate_key().decode()
