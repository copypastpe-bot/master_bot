"""Redesigned client Mini App endpoints."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.auth import extract_tg_id, validate_init_data
from src.config import APP_ENV, CLIENT_BOT_TOKEN
from src.database import (
    anonymize_client,
    confirm_order_by_client,
    create_review,
    get_client_activity_feed,
    get_client_by_tg_id,
    get_client_masters,
    get_client_orders_for_app,
    get_client_publications,
    get_master_by_id,
    get_master_client,
    get_master_public_profile,
    get_master_by_invite_token_public,
    get_review_by_order,
    get_reviews,
    get_services,
    update_client_notification_settings,
)
from src.models import Client, Master, MasterClient

router = APIRouter(tags=["client-app"])


def _review_response(review: dict) -> dict:
    return {
        "id": review["id"],
        "client_name": review.get("client_name") or "Клиент",
        "text": review["text"],
        "rating": review.get("rating"),
        "created_at": review.get("created_at"),
    }


async def _resolve_tg_id(x_init_data: Optional[str]) -> int:
    """Validate client initData and return Telegram user id."""
    if not x_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Init-Data header")
    if APP_ENV == "development" and x_init_data == "dev":
        return 999999999
    validated = validate_init_data(x_init_data, CLIENT_BOT_TOKEN)
    if not validated:
        raise HTTPException(status_code=401, detail="Invalid initData")
    tg_id = extract_tg_id(validated)
    if not tg_id:
        raise HTTPException(status_code=401, detail="No user data")
    return tg_id


async def _resolve_client(x_init_data: Optional[str]) -> Client:
    """Return authenticated client without choosing a master."""
    tg_id = await _resolve_tg_id(x_init_data)
    client = await get_client_by_tg_id(tg_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not registered")
    return client


async def _require_client_master(
    requested_master_id: int,
    x_init_data: Optional[str],
) -> tuple[Client, Master, MasterClient]:
    """Resolve a client against the path master_id."""
    client = await _resolve_client(x_init_data)
    master = await get_master_by_id(requested_master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    master_client = await get_master_client(master.id, client.id)
    if not master_client:
        raise HTTPException(status_code=403, detail="Not linked to this master")
    return client, master, master_client


@router.get("/client/master/{master_id}/profile")
async def get_client_master_profile(
    master_id: int,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client, master, master_client = await _require_client_master(master_id, x_init_data)
    profile = await get_master_public_profile(master.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Master not found")

    masters = await get_client_masters(client.id)
    current = next((item for item in masters if item["master_id"] == master.id), {})

    return {
        **profile,
        "bonus_balance": master_client.bonus_balance,
        "visit_count": current.get("visit_count") or current.get("order_count") or 0,
    }


@router.get("/client/master/{master_id}/activity")
async def get_client_master_activity(
    master_id: int,
    limit: int = Query(3, ge=1, le=50),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client, master, _master_client = await _require_client_master(master_id, x_init_data)
    items = await get_client_activity_feed(master.id, client.id, limit=limit, offset=0)
    return {"items": items}


@router.get("/client/master/{master_id}/history")
async def get_client_master_history(
    master_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client, master, master_client = await _require_client_master(master_id, x_init_data)
    items = await get_client_activity_feed(master.id, client.id, limit=limit, offset=offset)
    return {"items": items, "total": len(items), "bonus_balance": master_client.bonus_balance}


@router.get("/client/master/{master_id}/services")
async def get_client_master_services(
    master_id: int,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    _client, master, _master_client = await _require_client_master(master_id, x_init_data)
    services = await get_services(master.id, active_only=True)
    return {
        "services": [
            {
                "id": service.id,
                "name": service.name,
                "price": service.price,
                "description": service.description,
            }
            for service in services
        ]
    }


@router.get("/client/master/{master_id}/news")
async def get_client_master_news(
    master_id: int,
    limit: int = Query(1, ge=1, le=20),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    _client, master, _master_client = await _require_client_master(master_id, x_init_data)
    publications, total = await get_client_publications(master.id, limit=limit, offset=0)
    return {"publications": publications, "total": total}


@router.get("/client/master/{master_id}/publications")
async def get_client_master_publications(
    master_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    _client, master, _master_client = await _require_client_master(master_id, x_init_data)
    publications, total = await get_client_publications(master.id, limit=limit, offset=offset)
    return {"publications": publications, "total": total}


@router.get("/client/master/{master_id}/settings")
async def get_client_master_settings(
    master_id: int,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    _client, _master, master_client = await _require_client_master(master_id, x_init_data)
    return {
        "notify_reminders": master_client.notify_reminders,
        "notify_marketing": master_client.notify_marketing,
        "notify_bonuses": master_client.notify_bonuses,
    }


class ClientNotificationSettingsPatch(BaseModel):
    notify_reminders: Optional[bool] = None
    notify_marketing: Optional[bool] = None
    notify_bonuses: Optional[bool] = None


@router.patch("/client/master/{master_id}/settings")
async def patch_client_master_settings(
    master_id: int,
    body: ClientNotificationSettingsPatch,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client, master, _master_client = await _require_client_master(master_id, x_init_data)
    ok = await update_client_notification_settings(
        master_id=master.id,
        client_id=client.id,
        notify_reminders=body.notify_reminders,
        notify_marketing=body.notify_marketing,
        notify_bonuses=body.notify_bonuses,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Master-client link not found")
    return {"ok": True}


@router.post("/client/orders/{order_id}/confirm")
async def confirm_client_order(
    order_id: int,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client = await _resolve_client(x_init_data)
    ok = await confirm_order_by_client(order_id=order_id, client_id=client.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Order not found or cannot be confirmed")
    return {"ok": True, "client_confirmed": True, "display_status": "confirmed"}


class ReviewCreateRequest(BaseModel):
    text: str = Field(..., min_length=10)
    rating: Optional[int] = Field(None, ge=1, le=5)


@router.post("/client/orders/{order_id}/review")
async def create_client_order_review(
    order_id: int,
    body: ReviewCreateRequest,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client = await _resolve_client(x_init_data)
    masters = await get_client_masters(client.id)
    order = None
    master_id = None
    for item in masters:
        current_orders = await get_client_orders_for_app(
            item["master_id"],
            client.id,
            limit=100,
            offset=0,
        )
        order = next((current for current in current_orders if current["id"] == order_id), None)
        if order:
            master_id = item["master_id"]
            break
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("status") != "done":
        raise HTTPException(status_code=409, detail="Review is available only for completed orders")
    if await get_review_by_order(order_id):
        raise HTTPException(status_code=409, detail="Review already exists")

    review_id = await create_review(
        master_id=master_id,
        client_id=client.id,
        order_id=order_id,
        text=body.text.strip(),
        rating=body.rating,
    )
    return {"ok": True, "review_id": review_id}


@router.get("/client/master/{master_id}/reviews")
async def get_client_master_reviews(
    master_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    _client, master, _master_client = await _require_client_master(master_id, x_init_data)
    reviews = await get_reviews(master.id, limit=limit, offset=offset)
    return {"reviews": [_review_response(review) for review in reviews], "total": len(reviews)}


@router.get("/public/master/{invite_token}")
async def get_public_master(invite_token: str):
    profile = await get_master_by_invite_token_public(invite_token)
    if not profile:
        raise HTTPException(status_code=404, detail="Master not found")
    services = await get_services(profile["id"], active_only=True)
    reviews = await get_reviews(profile["id"], limit=10, offset=0)
    return {
        **profile,
        "services": [
            {
                "id": service.id,
                "name": service.name,
                "price": service.price,
                "description": service.description,
            }
            for service in services
        ],
        "reviews": [_review_response(review) for review in reviews],
    }


@router.delete("/client/profile")
async def delete_client_profile(
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    client = await _resolve_client(x_init_data)
    ok = await anonymize_client(client.id)
    return {"ok": ok}
