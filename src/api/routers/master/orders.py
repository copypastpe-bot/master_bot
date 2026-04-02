"""Master orders endpoints — GET detail, create, complete, move, cancel."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from src.api.dependencies import get_current_master
from src.database import (
    get_order_by_id,
    get_order_items,
    get_master_client,
    get_client_by_id,
    create_order,
    create_order_items,
    get_services,
)
from src.models import Master
from src.services.orders import (
    complete_order_service,
    move_order_service,
    cancel_order_service,
)
from src import notifications
from src import google_calendar

logger = logging.getLogger(__name__)

router = APIRouter(tags=["master"])


def _format_order_detail(order: dict, items: list[dict], mc) -> dict:
    """Format a full order detail response."""
    scheduled_at = order.get("scheduled_at") or ""
    return {
        "id": order["id"],
        "scheduled_at": scheduled_at,
        "client": {
            "id": order.get("client_id"),
            "name": order.get("client_name") or "",
            "phone": order.get("client_phone") or "",
            "tg_id": order.get("client_tg_id"),
            "bonus_balance": mc.bonus_balance if mc else 0,
        },
        "services": items,
        "amount_total": order.get("amount_total") or 0,
        "status": order.get("status", "new"),
        "address": order.get("address") or "",
        "bonus_spent": order.get("bonus_spent") or 0,
        "bonus_accrued": order.get("bonus_accrued") or 0,
        "payment_type": order.get("payment_type"),
        "note": order.get("note") or "",
        "created_at": order.get("created_at") or "",
        "done_at": order.get("done_at") or "",
        "gc_event_id": order.get("gc_event_id"),
        "cancel_reason": order.get("cancel_reason") or "",
    }


@router.get("/master/orders/{order_id}")
async def get_master_order_detail(
    order_id: int,
    request: Request,
    master: Master = Depends(get_current_master),
):
    """Get full order details."""
    order = await get_order_by_id(order_id, master.id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = await get_order_items(order_id)
    mc = await get_master_client(master.id, order.get("client_id"))

    return _format_order_detail(order, items, mc)


class OrderServiceItem(BaseModel):
    service_id: Optional[int] = None
    name: Optional[str] = None
    price: int

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("price must be positive")
        return v


class CreateOrderBody(BaseModel):
    client_id: int
    services: list[OrderServiceItem]
    scheduled_date: str  # YYYY-MM-DD
    scheduled_time: str  # HH:MM
    address: str = ""


@router.post("/master/orders")
async def create_master_order(
    body: CreateOrderBody,
    request: Request,
    master: Master = Depends(get_current_master),
):
    """Create a new order."""
    # Validate client belongs to this master
    mc = await get_master_client(master.id, body.client_id)
    if not mc:
        raise HTTPException(status_code=404, detail="Client not found or not linked to master")

    # Parse scheduled_at
    try:
        scheduled_at = datetime.fromisoformat(f"{body.scheduled_date}T{body.scheduled_time}:00")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date or time format")

    # Resolve service names from service_id if provided
    master_services_map: dict[int, str] = {}
    service_ids = [s.service_id for s in body.services if s.service_id is not None]
    if service_ids:
        all_services = await get_services(master.id, active_only=False)
        master_services_map = {s.id: s.name for s in all_services}

    order_items: list[dict] = []
    for svc in body.services:
        if svc.service_id is not None:
            svc_name = master_services_map.get(svc.service_id)
            if not svc_name:
                raise HTTPException(
                    status_code=400,
                    detail=f"Service {svc.service_id} not found"
                )
            order_items.append({"name": svc_name, "price": svc.price})
        elif svc.name:
            order_items.append({"name": svc.name.strip(), "price": svc.price})
        else:
            raise HTTPException(status_code=400, detail="Each service must have service_id or name")

    amount_total = sum(item["price"] for item in order_items)

    # Create order
    order_id = await create_order(
        master_id=master.id,
        client_id=body.client_id,
        address=body.address,
        scheduled_at=scheduled_at,
        amount_total=amount_total,
        status="new",
    )

    # Create order items
    await create_order_items(order_id, order_items)

    # Fetch client once — used for both GC and notifications below
    client = await get_client_by_id(body.client_id)

    # GC: create event (optional, no crash on failure)
    try:
        if client:
            services_text = ", ".join(item["name"] for item in order_items)
            gc_event_id = await google_calendar.create_event(
                master_id=master.id,
                client_name=client.name or "",
                client_phone=client.phone or "",
                services=services_text,
                address=body.address,
                amount=amount_total,
                scheduled_at=scheduled_at,
            )
            if gc_event_id:
                from src.database import update_order_status
                await update_order_status(order_id, "new", gc_event_id=gc_event_id)
    except Exception as e:
        logger.warning(f"GC create_event failed (order {order_id}): {e}")

    # Notify client via module-level client_bot
    try:
        if client and client.tg_id:
            await notifications.notify_order_created(
                client=client,
                order={
                    "id": order_id,
                    "scheduled_at": scheduled_at,
                    "address": body.address,
                    "amount_total": amount_total,
                },
                master=master,
                services=order_items,
            )
    except Exception as e:
        logger.error(f"Failed to notify client (create order {order_id}): {e}")

    order = await get_order_by_id(order_id, master.id)
    items = await get_order_items(order_id)
    mc_updated = await get_master_client(master.id, body.client_id)

    return _format_order_detail(order, items, mc_updated)


class CompleteOrderBody(BaseModel):
    amount: int
    payment_type: str
    bonus_spent: int = 0


@router.put("/master/orders/{order_id}/complete")
async def complete_master_order(
    order_id: int,
    body: CompleteOrderBody,
    request: Request,
    master: Master = Depends(get_current_master),
):
    """Complete an order with payment and bonus logic."""
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")
    if body.bonus_spent < 0:
        raise HTTPException(status_code=400, detail="bonus_spent cannot be negative")

    valid_payment_types = ("cash", "card", "transfer", "invoice")
    if body.payment_type not in valid_payment_types:
        raise HTTPException(
            status_code=400,
            detail=f"payment_type must be one of: {', '.join(valid_payment_types)}"
        )

    # Get client_bot from app.state if available
    client_bot = getattr(request.app.state, "client_bot", None)

    try:
        result = await complete_order_service(
            order_id=order_id,
            master=master,
            amount=body.amount,
            payment_type=body.payment_type,
            bonus_spent=body.bonus_spent,
            bot=client_bot,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    updated_order = result["updated_order"]
    items = await get_order_items(order_id)
    mc = await get_master_client(master.id, updated_order.get("client_id"))

    return {
        "success": True,
        "bonus_accrued": result["bonus_accrued"],
        "bonus_spent": result["bonus_spent"],
        "new_balance": result["new_balance"],
        "order": _format_order_detail(updated_order, items, mc),
    }


class MoveOrderBody(BaseModel):
    new_date: str  # YYYY-MM-DD
    new_time: str  # HH:MM


@router.put("/master/orders/{order_id}/move")
async def move_master_order(
    order_id: int,
    body: MoveOrderBody,
    request: Request,
    master: Master = Depends(get_current_master),
):
    """Move (reschedule) an order."""
    client_bot = getattr(request.app.state, "client_bot", None)

    try:
        result = await move_order_service(
            order_id=order_id,
            master=master,
            new_date=body.new_date,
            new_time=body.new_time,
            bot=client_bot,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    updated_order = result["updated_order"]
    items = await get_order_items(order_id)
    mc = await get_master_client(master.id, updated_order.get("client_id"))

    return {
        "success": True,
        "order": _format_order_detail(updated_order, items, mc),
    }


class CancelOrderBody(BaseModel):
    reason: Optional[str] = None


@router.put("/master/orders/{order_id}/cancel")
async def cancel_master_order(
    order_id: int,
    body: CancelOrderBody,
    request: Request,
    master: Master = Depends(get_current_master),
):
    """Cancel an order."""
    client_bot = getattr(request.app.state, "client_bot", None)

    try:
        result = await cancel_order_service(
            order_id=order_id,
            master=master,
            reason=body.reason,
            bot=client_bot,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    updated_order = result["updated_order"]
    items = await get_order_items(order_id)
    mc = await get_master_client(master.id, updated_order.get("client_id"))

    return {
        "success": True,
        "order": _format_order_detail(updated_order, items, mc),
    }
