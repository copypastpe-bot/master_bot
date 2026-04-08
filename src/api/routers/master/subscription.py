"""Master subscription endpoints."""

import logging
from contextlib import suppress
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import LabeledPrice
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_current_master
from src.config import SUBSCRIPTION_PLANS, MASTER_BOT_USERNAME, MASTER_BOT_TOKEN
from src.database import get_subscription_status
from src.models import Master
from src.subscription_stars import build_invoice_payload

logger = logging.getLogger(__name__)

router = APIRouter(tags=["master-subscription"])
_master_bot: Optional[Bot] = None


def set_master_bot(bot: Bot) -> None:
    """Inject shared master bot instance from server bootstrap."""
    global _master_bot
    _master_bot = bot


async def _get_master_bot() -> tuple[Bot, bool]:
    """Return bot instance and ownership flag for lifecycle management."""
    if _master_bot is not None:
        return _master_bot, False
    return Bot(token=MASTER_BOT_TOKEN), True


def _serialize_status(status: dict) -> dict:
    history = []
    for item in status.get("payment_history", []):
        history.append({
            **item,
            "subscription_until": item["subscription_until"].isoformat() if item.get("subscription_until") else None,
            "created_at": item["created_at"].isoformat() if item.get("created_at") else None,
        })
    return {
        "is_active": status["is_active"],
        "subscription_until": status["subscription_until"].isoformat() if status["subscription_until"] else None,
        "days_left": status["days_left"],
        "is_trial": status["is_trial"],
        "referral_code": status["referral_code"],
        "referral_count": status["referral_count"],
        "payment_history": history,
    }


@router.get("/master/subscription")
async def get_master_subscription(
    master: Master = Depends(get_current_master),
):
    """Get subscription status with payment history and referral info."""
    status = await get_subscription_status(master.id)
    data = _serialize_status(status)

    bot_username = (MASTER_BOT_USERNAME or "").lstrip("@")
    code = status["referral_code"]
    data["referral_link"] = (
        f"https://t.me/{bot_username}/app?startapp=ref_{code}"
        if bot_username
        else None
    )
    return data


class SubscriptionInvoiceBody(BaseModel):
    payload: str


@router.post("/master/subscription/invoice-link")
async def post_master_subscription_invoice_link(
    body: SubscriptionInvoiceBody,
    master: Master = Depends(get_current_master),
):
    """Create Telegram Stars invoice link for selected subscription plan."""
    if body.payload not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=422, detail="Unknown plan payload")

    plan = SUBSCRIPTION_PLANS[body.payload]
    stars_amount = int(plan["stars"])
    plan_label = str(plan["label"])
    invoice_payload = build_invoice_payload(master.id, body.payload)

    bot, owns_bot = await _get_master_bot()
    try:
        invoice_link = await bot.create_invoice_link(
            title=f"Подписка CRMfit · {plan_label}",
            description=f"Продление подписки на {plan_label}",
            payload=invoice_payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=plan_label, amount=stars_amount)],
        )
    except TelegramAPIError as e:
        logger.exception(
            "Failed to create Stars invoice link: master_id=%s payload=%s error=%s",
            master.id,
            body.payload,
            e,
        )
        raise HTTPException(status_code=502, detail="Failed to create invoice link")
    finally:
        if owns_bot:
            with suppress(Exception):
                await bot.session.close()

    return {
        "invoice_link": invoice_link,
        "payload": body.payload,
        "stars_amount": stars_amount,
        "plan_label": plan_label,
    }


class ReferralCopyBody(BaseModel):
    source: Optional[str] = None


@router.post("/master/subscription/referral-link-copied")
async def post_referral_link_copied(
    body: Optional[ReferralCopyBody] = None,
    master: Master = Depends(get_current_master),
):
    """Analytics stub: log referral-link copy action."""
    logger.info(
        "Referral link copied: master_id=%s source=%s",
        master.id,
        body.source if body else "unknown",
    )
    return {"ok": True}
