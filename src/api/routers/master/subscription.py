"""Master subscription endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_current_master
from src.config import SUBSCRIPTION_PLANS, MASTER_BOT_USERNAME
from src.database import apply_payment, get_subscription_status
from src.models import Master

logger = logging.getLogger(__name__)

router = APIRouter(tags=["master-subscription"])


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


class SubscriptionPaymentBody(BaseModel):
    telegram_charge_id: str
    payload: str
    stars_amount: int


@router.post("/master/subscription/payment")
async def post_master_subscription_payment(
    body: SubscriptionPaymentBody,
    master: Master = Depends(get_current_master),
):
    """Apply Stars payment and return updated subscription."""
    if body.payload not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=422, detail="Unknown plan payload")

    try:
        result = await apply_payment(
            master_id=master.id,
            telegram_charge_id=body.telegram_charge_id,
            payload=body.payload,
            stars_amount=body.stars_amount,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    plan = SUBSCRIPTION_PLANS[body.payload]
    subscription_until = result["subscription_until"]
    if hasattr(subscription_until, "isoformat"):
        subscription_until = subscription_until.isoformat()

    return {
        "subscription_until": subscription_until,
        "days_added": result["days_added"],
        "plan_label": plan["label"],
        "duplicate": result["duplicate"],
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
