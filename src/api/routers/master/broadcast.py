"""Master broadcast endpoints — segments, preview, send."""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional

from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import BufferedInputFile
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from src.api.dependencies import get_current_master
from src.api.ratelimit import broadcast_limiter
from src.config import CLIENT_BOT_USERNAME
from src.database import (
    create_broadcast_campaign,
    get_broadcast_recipients_count,
    get_broadcast_status,
    get_clients_by_segment,
)
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

    if not getattr(request.app.state, "client_bot", None):
        raise HTTPException(status_code=503, detail="client_bot not available")

    # Persist media to disk so a container restart mid-flight can still
    # read the bytes (the worker re-loads them by path).
    media_path: Optional[str] = None
    if media_bytes:
        media_dir = Path(os.getenv("BROADCAST_MEDIA_DIR", "/app/data/broadcast"))
        try:
            media_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            media_dir = Path("/tmp/master_bot_broadcast")
            media_dir.mkdir(parents=True, exist_ok=True)
        suffix = ".jpg" if media_type == "photo" else ".mp4"
        media_path = str(media_dir / f"campaign_{master.id}_{int(time.time())}{suffix}")
        Path(media_path).write_bytes(media_bytes)

    campaign_id = await create_broadcast_campaign(
        master_id=master.id,
        text=text,
        segment=segment,
        recipients=[
            # get_clients_by_segment returns id/tg_id/name; rename id → client_id.
            {"client_id": r["id"], "tg_id": r["tg_id"]}
            for r in recipients if r.get("tg_id")
        ],
        media_path=media_path,
        media_type=media_type if media_bytes else None,
    )

    # Fire-and-forget. Restart-safe: campaigns.status + broadcast_recipients
    # carry enough state that a startup hook can pick up where this left off.
    asyncio.create_task(_run_broadcast(campaign_id, request.app))

    return JSONResponse(
        status_code=202,
        content={"campaign_id": campaign_id, "total_recipients": len(recipients)},
    )


@router.get("/master/broadcast/campaigns/{campaign_id}")
async def get_broadcast_campaign_status(
    campaign_id: int,
    master: Master = Depends(get_current_master),
):
    """Polled by the Mini App after POST /send returns 202."""
    status = await get_broadcast_status(campaign_id)
    if not status:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if status["master_id"] != master.id:
        raise HTTPException(status_code=403, detail="Not your campaign")
    return {
        "campaign_id": campaign_id,
        "status": status["status"],
        "total_recipients": status["total_recipients"],
        "sent_count": status["sent_count"],
        "failed_count": status["failed_count"],
        "last_progress_at": status["last_progress_at"],
    }


async def _run_broadcast(campaign_id: int, app, *, sleep_seconds: float = 0.05) -> None:
    """Background worker that drains broadcast_recipients for a campaign.

    Idempotent and restart-safe: only touches rows still in 'pending', so a
    re-launched run after crash picks up exactly where the previous one
    stopped. Reads media bytes from disk when campaigns.media_path is set,
    so the bytes survive a container restart.
    """
    from pathlib import Path
    from src.database import (
        get_broadcast_status,
        get_master_by_id,
        get_pending_broadcast_recipients,
        mark_broadcast_recipient_sent,
        mark_broadcast_recipient_failed,
        set_broadcast_status,
        finalize_broadcast,
    )

    campaign = await get_broadcast_status(campaign_id)
    if not campaign:
        logger.warning(f"broadcast worker: campaign {campaign_id} not found")
        return

    master = await get_master_by_id(campaign["master_id"])
    if not master:
        await set_broadcast_status(campaign_id, "failed")
        return

    client_bot = getattr(app.state, "client_bot", None)
    if not client_bot:
        logger.error(f"broadcast {campaign_id}: client_bot not on app.state — marking failed")
        await set_broadcast_status(campaign_id, "failed")
        return

    media_bytes: Optional[bytes] = None
    media_type = campaign["media_type"]
    if campaign["media_path"]:
        try:
            media_bytes = Path(campaign["media_path"]).read_bytes()
        except FileNotFoundError:
            logger.error(f"broadcast {campaign_id}: media file missing — sending text only")
            media_type = None

    await set_broadcast_status(campaign_id, "running")

    text = campaign["text"]

    while True:
        batch = await get_pending_broadcast_recipients(campaign_id, limit=50)
        if not batch:
            break

        for recipient in batch:
            tg_id = recipient["tg_id"]
            client_id = recipient["client_id"]
            body = _personalize(text, recipient.get("name") or "")
            personalized = f"{master.name}:\n\n{body}"
            try:
                if media_bytes and media_type == "photo":
                    file_obj = BufferedInputFile(media_bytes, filename="photo.jpg")
                    await client_bot.send_photo(chat_id=tg_id, photo=file_obj, caption=personalized)
                elif media_bytes and media_type == "video":
                    file_obj = BufferedInputFile(media_bytes, filename="video.mp4")
                    await client_bot.send_video(chat_id=tg_id, video=file_obj, caption=personalized)
                else:
                    await client_bot.send_message(chat_id=tg_id, text=personalized)
                await mark_broadcast_recipient_sent(campaign_id, client_id=client_id)
            except TelegramForbiddenError:
                await mark_broadcast_recipient_failed(
                    campaign_id, client_id=client_id, error="blocked", blocked=True,
                )
            except Exception as e:  # noqa: BLE001 — log + persist, never crash the worker
                logger.error(f"broadcast {campaign_id} → {tg_id}: {e}")
                await mark_broadcast_recipient_failed(
                    campaign_id, client_id=client_id, error=str(e),
                )
            if sleep_seconds:
                await asyncio.sleep(sleep_seconds)

    await finalize_broadcast(campaign_id)
