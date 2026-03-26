"""Master promos endpoints — list, create, deactivate."""

import asyncio
import logging
from datetime import date
from typing import Optional

from aiogram.exceptions import TelegramForbiddenError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from src.api.dependencies import get_current_master
from src.database import (
    get_active_promos,
    get_promo_by_id,
    save_campaign,
    deactivate_promo,
    get_clients_by_segment,
    get_marketing_recipients_count,
    get_connection,
)
from src.models import Master

logger = logging.getLogger(__name__)

router = APIRouter(tags=["master-promos"])


def _fmt_promo(p) -> dict:
    return {
        "id": p.id,
        "title": p.title or "",
        "text": p.text or "",
        "active_from": p.active_from,
        "active_to": p.active_to,
        "sent_count": p.sent_count or 0,
        "created_at": str(p.created_at or "")[:10],
    }


async def _get_past_promos(master_id: int, limit: int = 10):
    """Get past (expired) promo campaigns for a master."""
    conn = await get_connection()
    try:
        today = date.today().isoformat()
        cursor = await conn.execute(
            """
            SELECT * FROM campaigns
            WHERE master_id = ?
              AND type = 'promo'
              AND active_to < ?
            ORDER BY active_to DESC
            LIMIT ?
            """,
            (master_id, today, limit),
        )
        rows = await cursor.fetchall()
        from src.models import Campaign
        return [
            Campaign(
                id=row["id"],
                master_id=row["master_id"],
                type=row["type"],
                title=row["title"],
                text=row["text"],
                active_from=row["active_from"],
                active_to=row["active_to"],
                segment=row["segment"],
                sent_at=row["sent_at"],
                sent_count=row["sent_count"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# GET /master/promos
# ---------------------------------------------------------------------------

@router.get("/master/promos")
async def get_master_promos(
    master: Master = Depends(get_current_master),
):
    """Return active and past promo campaigns."""
    active = await get_active_promos(master.id)
    past = await _get_past_promos(master.id, limit=10)

    return {
        "active": [_fmt_promo(p) for p in active],
        "past": [_fmt_promo(p) for p in past],
    }


# ---------------------------------------------------------------------------
# POST /master/promos
# ---------------------------------------------------------------------------

class PromoCreateBody(BaseModel):
    title: str
    text: str
    active_from: str
    active_to: str
    notify_clients: bool = False

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError("title required")
        return v

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v):
        if not v.strip():
            raise ValueError("text required")
        return v

    @field_validator("active_to")
    @classmethod
    def dates_valid(cls, v, info):
        active_from = info.data.get("active_from")
        if active_from and v <= active_from:
            raise ValueError("active_to must be after active_from")
        return v


@router.post("/master/promos")
async def create_master_promo(
    body: PromoCreateBody,
    request: Request,
    master: Master = Depends(get_current_master),
):
    """Create a promo campaign, optionally notifying clients."""
    sent_count = 0

    if body.notify_clients:
        client_bot = getattr(request.app.state, "client_bot", None)
        if client_bot:
            recipients = await get_clients_by_segment(master.id, "all")
            promo_text = f"🎉 {body.title}\n\n{body.text}"
            for client in recipients:
                tg_id = client.get("tg_id")
                if not tg_id:
                    continue
                try:
                    await client_bot.send_message(chat_id=tg_id, text=promo_text)
                    sent_count += 1
                    await asyncio.sleep(0.05)
                except TelegramForbiddenError:
                    logger.warning(f"Promo notify: client {tg_id} blocked the bot")
                except Exception as e:
                    logger.error(f"Promo notify: failed to send to {tg_id}: {e}")

    campaign = await save_campaign(
        master_id=master.id,
        campaign_type="promo",
        title=body.title,
        text=body.text,
        active_from=body.active_from,
        active_to=body.active_to,
        sent_count=sent_count,
    )

    return {**_fmt_promo(campaign), "sent_count": sent_count}


# ---------------------------------------------------------------------------
# GET /master/promos/recipients-count — for PromoCreate step 3
# ---------------------------------------------------------------------------

@router.get("/master/promos/recipients-count")
async def get_promo_recipients_count(
    master: Master = Depends(get_current_master),
):
    """Count of clients who can receive promo notifications."""
    count = await get_marketing_recipients_count(master.id)
    return {"count": count}


# ---------------------------------------------------------------------------
# PUT /master/promos/{promo_id}/deactivate
# ---------------------------------------------------------------------------

@router.put("/master/promos/{promo_id}/deactivate")
async def deactivate_master_promo(
    promo_id: int,
    master: Master = Depends(get_current_master),
):
    """Deactivate a promo (set active_to = yesterday)."""
    promo = await get_promo_by_id(promo_id, master.id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promo not found")

    await deactivate_promo(promo_id, master.id)
    return {"ok": True}
