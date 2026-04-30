"""Master broadcast endpoints — segments, preview, send."""

import asyncio
import logging
from typing import Optional

from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, field_validator

from src.api.dependencies import get_current_master
from src.api.ratelimit import broadcast_limiter
from src.config import CLIENT_BOT_USERNAME
from src.database import get_clients_by_segment, save_campaign, get_broadcast_recipients_count
from src.models import Master
from src.notifications import open_app_button

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
    has_media: bool = False
    media_type: Optional[str] = None  # "photo" | "video" | None

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



PHOTO_MAX_BYTES = 10 * 1024 * 1024   # 10 MB
VIDEO_MAX_BYTES = 50 * 1024 * 1024   # 50 MB


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


@router.get("/master/broadcast/can-send")
async def get_broadcast_can_send(
    master: Master = Depends(get_current_master),
):
    """Check if master can send broadcasts (has clients with Telegram)."""
    count = await get_broadcast_recipients_count(master.id, "all")
    bot_username = CLIENT_BOT_USERNAME or "client_bot"
    invite_link = f"https://t.me/{bot_username}?start=invite_{master.invite_token}"
    return {
        "can_send": count > 0,
        "clients_with_telegram": count,
        "invite_link": invite_link,
    }


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
        "has_media": body.has_media,
        "media_type": body.media_type,
    }


@router.post("/master/broadcast/send")
async def send_broadcast(
    request: Request,
    segment: str = Form(...),
    text: str = Form(...),
    media_type: Optional[str] = Form(None),
    media: Optional[UploadFile] = File(None),
    master: Master = Depends(get_current_master),
):
    """Send broadcast to selected segment via client_bot."""
    # Rate limit: 2 broadcasts per master per 5 minutes
    if not broadcast_limiter.is_allowed(f"master:{master.id}"):
        raise HTTPException(
            status_code=429,
            detail="Рассылка отправляется слишком часто. Подождите несколько минут.",
        )

    # Validate segment
    if segment not in VALID_SEGMENTS:
        raise HTTPException(status_code=422, detail="Unknown segment")

    # Validate text
    text = text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text cannot be empty")
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=422, detail=f"text exceeds {MAX_TEXT_LENGTH} characters")

    # Read and validate media
    media_bytes: Optional[bytes] = None
    if media is not None and media_type in ("photo", "video"):
        media_bytes = await media.read()
        limit = PHOTO_MAX_BYTES if media_type == "photo" else VIDEO_MAX_BYTES
        if len(media_bytes) > limit:
            limit_mb = limit // (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"{media_type} exceeds {limit_mb} MB limit",
            )

    recipients = await get_clients_by_segment(master.id, segment)

    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients in this segment")

    client_bot = getattr(request.app.state, "client_bot", None)
    if not client_bot:
        raise HTTPException(status_code=503, detail="client_bot not available")

    sent = 0
    failed = 0
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[open_app_button(master_id=master.id)]])

    for client in recipients:
        tg_id = client.get("tg_id")
        if not tg_id:
            failed += 1
            continue
        try:
            personalized_body = _personalize(text, client.get("name") or "")
            personalized = f"{master.name}:\n\n{personalized_body}"
            if media_bytes and media_type == "photo":
                file_obj = BufferedInputFile(media_bytes, filename="photo.jpg")
                await client_bot.send_photo(chat_id=tg_id, photo=file_obj, caption=personalized, reply_markup=reply_markup)
            elif media_bytes and media_type == "video":
                file_obj = BufferedInputFile(media_bytes, filename="video.mp4")
                await client_bot.send_video(chat_id=tg_id, video=file_obj, caption=personalized, reply_markup=reply_markup)
            else:
                await client_bot.send_message(chat_id=tg_id, text=personalized, reply_markup=reply_markup)
            sent += 1
            await asyncio.sleep(0.05)  # 50 ms rate-limit pause
        except TelegramForbiddenError:
            logger.warning(f"Broadcast: client {tg_id} blocked the bot")
            failed += 1
        except Exception as e:
            logger.error(f"Broadcast: failed to send to {tg_id}: {e}")
            failed += 1

    await save_campaign(
        master_id=master.id,
        campaign_type="broadcast",
        title=None,
        text=text,
        active_from=None,
        active_to=None,
        sent_count=sent,
        segment=segment,
    )

    return {"sent_count": sent, "failed_count": failed}
