"""Master calendar endpoints — orders by date and active dates for month."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_current_master
from src.database import get_orders_by_date, get_active_dates
from src.models import Master

router = APIRouter(tags=["master"])


def _format_calendar_order(order: dict) -> dict:
    """Format a raw order dict for the calendar response."""
    scheduled_at = order.get("scheduled_at", "")

    # Extract HH:MM from ISO datetime string
    time_str = ""
    if scheduled_at:
        try:
            time_str = scheduled_at[11:16]  # "HH:MM"
        except Exception:
            time_str = ""

    client_name = order.get("client_name", "")
    parts = client_name.split() if client_name else []
    if len(parts) >= 2:
        client_name_short = f"{parts[0]} {parts[1][0]}."
    else:
        client_name_short = client_name

    # Format phone
    phone = order.get("client_phone", "") or ""

    return {
        "id": order["id"],
        "scheduled_at": scheduled_at,
        "time": time_str,
        "client_name": client_name_short,
        "client_phone": phone,
        "services": order.get("services") or "",
        "amount_total": order.get("amount_total") or 0,
        "status": order.get("status", "new"),
        "address": order.get("address") or "",
    }


@router.get("/master/orders")
async def get_orders_for_date(
    date_str: str = Query(..., alias="date"),
    master: Master = Depends(get_current_master),
):
    """Get all orders for a specific date (all statuses)."""
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    orders_raw = await get_orders_by_date(master.id, target_date, all_statuses=True)

    return {
        "date": date_str,
        "orders": [_format_calendar_order(o) for o in orders_raw],
    }


@router.get("/master/orders/dates")
async def get_order_dates(
    year: int = Query(...),
    month: int = Query(...),
    master: Master = Depends(get_current_master),
):
    """Get dates that have orders for a given month (for calendar dot markers)."""
    active_dates = await get_active_dates(master.id, year, month)

    return {
        "dates": [d.isoformat() for d in active_dates],
    }
