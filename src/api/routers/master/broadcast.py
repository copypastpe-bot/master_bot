"""Master broadcast endpoints — segments, preview, send."""

import asyncio
import logging
from typing import Optional

from aiogram.exceptions import TelegramForbiddenError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from src.api.dependencies import get_current_master
from src.database import get_clients_by_segment, save_campaign
from src.models import Master

logger = logging.getLogger(__name__)

router = APIRouter(tags=["master"])

SEGMENT_DEFINITIONS = [
    {"id": "all", "name": "Все клиенты"},
    {"id": "active", "name": "Активные (заказ за 30 дней)"},
    {"id": "inactive", "name": "Спящие (нет заказов 60+ дней)"},
    {"id": "new", "name": "Новые (за 30 дней)"},
    {"id": "birthday_month", "name": "День рождения в этом месяце"},
]

VALID_SEGMENTS = {s["id"] for s in SEGMENT_DEFINITIONS}
MAX_TEXT_LENGTH = 1000


class PreviewRequest(BaseModel):
    segment: str
    text: str

    @field_validator("segment")
    @classmethod
    def validate_segment(cls, v: str) -> str:
        if v not in VALID_SEGMENTS:
            raise ValueError(f"Unknown segment: {v}")
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text cannot be empty")
        if len(v) > MAX_TEXT_LENGTH:
            raise ValueError(f"text exceeds {MAX_TEXT_LENGTH} characters")
        return v


class SendRequest(BaseModel):
    segment: str
    text: str

    @field_validator("segment")
    @classmethod
    def validate_segment(cls, v: str) -> str:
        if v not in VALID_SEGMENTS:
            raise ValueError(f"Unknown segment: {v}")
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text cannot be empty")
        if len(v) > MAX_TEXT_LENGTH:
            raise ValueError(f"text exceeds {MAX_TEXT_LENGTH} characters")
        return v


def _personalize(text: str, name: str) -> str:
    """Replace {name} placeholder with client's first name."""
    stripped = (name or "").strip()
    first_name = stripped.split()[0] if stripped else "клиент"
    return text.replace("{name}", first_name)


def _abbreviate_name(name: str) -> str:
    """Return 'Имя Ф.' abbreviated format."""
    parts = name.split() if name else []
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1][0]}."
    return name


@router.get("/master/broadcast/segments")
async def get_broadcast_segments(
    master: Master = Depends(get_current_master),
):
    """Return all segments with recipient counts."""
    segments = []
    for seg_def in SEGMENT_DEFINITIONS:
        recipients = await get_clients_by_segment(master.id, seg_def["id"])
        segments.append({
            "id": seg_def["id"],
            "name": seg_def["name"],
            "count": len(recipients),
        })
    return {"segments": segments}


@router.post("/master/broadcast/preview")
async def preview_broadcast(
    body: PreviewRequest,
    master: Master = Depends(get_current_master),
):
    """Preview broadcast — return personalized example and sample recipients."""
    recipients = await get_clients_by_segment(master.id, body.segment)

    preview_text = body.text
    sample_recipients = []

    if recipients:
        # Use first recipient's name for preview
        first_name = recipients[0].get("name") or "Клиент"
        preview_text = _personalize(body.text, first_name)
        sample_recipients = [
            _abbreviate_name(r["name"]) for r in recipients[:3]
        ]

    return {
        "recipients_count": len(recipients),
        "preview_text": preview_text,
        "sample_recipients": sample_recipients,
    }


@router.post("/master/broadcast/send")
async def send_broadcast(
    body: SendRequest,
    request: Request,
    master: Master = Depends(get_current_master),
):
    """Send broadcast to selected segment via client_bot."""
    recipients = await get_clients_by_segment(master.id, body.segment)

    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients in this segment")

    client_bot = getattr(request.app.state, "client_bot", None)
    if not client_bot:
        raise HTTPException(status_code=503, detail="client_bot not available")

    sent = 0
    failed = 0

    for client in recipients:
        tg_id = client.get("tg_id")
        if not tg_id:
            failed += 1
            continue
        try:
            text = _personalize(body.text, client.get("name") or "")
            await client_bot.send_message(chat_id=tg_id, text=text)
            sent += 1
            await asyncio.sleep(0.05)  # 50 ms rate-limit pause
        except TelegramForbiddenError:
            logger.warning(f"Broadcast: client {tg_id} blocked the bot")
            failed += 1
        except Exception as e:
            logger.error(f"Broadcast: failed to send to {tg_id}: {e}")
            failed += 1

    # Persist campaign record
    await save_campaign(
        master_id=master.id,
        campaign_type="broadcast",
        title=None,
        text=body.text,
        active_from=None,
        active_to=None,
        sent_count=sent,
        segment=body.segment,
    )

    return {"sent_count": sent, "failed_count": failed}
