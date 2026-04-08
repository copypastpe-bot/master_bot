"""Helpers for Telegram Stars invoice payloads."""

import secrets
import time
from dataclasses import dataclass
from typing import Optional

PAYLOAD_PREFIX = "sub"


@dataclass(frozen=True)
class ParsedInvoicePayload:
    """Parsed and validated subscription invoice payload."""

    master_id: int
    plan_payload: str
    issued_at: int
    nonce: str


def build_invoice_payload(master_id: int, plan_payload: str) -> str:
    """Build compact invoice payload with master, plan, timestamp and nonce."""
    nonce = secrets.token_hex(4)
    issued_at = int(time.time())
    return f"{PAYLOAD_PREFIX}:{master_id}:{plan_payload}:{issued_at}:{nonce}"


def parse_invoice_payload(raw_payload: str) -> Optional[ParsedInvoicePayload]:
    """Parse invoice payload from Telegram successful payment update."""
    text = (raw_payload or "").strip()
    parts = text.split(":")
    if len(parts) != 5:
        return None

    prefix, master_id_raw, plan_payload, issued_at_raw, nonce = parts
    if prefix != PAYLOAD_PREFIX:
        return None
    if not master_id_raw.isdigit():
        return None
    if not issued_at_raw.isdigit():
        return None
    if not plan_payload:
        return None
    if not nonce or len(nonce) > 32:
        return None

    try:
        master_id = int(master_id_raw)
        issued_at = int(issued_at_raw)
    except ValueError:
        return None

    return ParsedInvoicePayload(
        master_id=master_id,
        plan_payload=plan_payload,
        issued_at=issued_at,
        nonce=nonce,
    )
