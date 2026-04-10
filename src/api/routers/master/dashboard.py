"""Master profile/dashboard endpoint."""

from datetime import date, timedelta
from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_master
from src.database import (
    get_clients_paginated,
    get_orders_by_date,
    get_reports,
    count_pending_requests,
    count_done_orders,
)
from src.models import Master
from src.config import CLIENT_BOT_USERNAME

router = APIRouter(tags=["master"])


def _legacy_contacts(master: Master) -> str | None:
    return master.contacts or master.phone


def _legacy_socials(master: Master) -> str | None:
    if master.socials:
        return master.socials
    parts = [p for p in [master.telegram, master.instagram, master.website] if p]
    return " · ".join(parts) if parts else None


@router.get("/master/me")
async def get_master_me(
    master: Master = Depends(get_current_master)
):
    """Get current master's profile and summary stats."""
    # Use paginated query with per_page=1 — we only need the total_count
    _clients, client_count = await get_clients_paginated(master.id, page=1, per_page=1)

    return {
        "id": master.id,
        "name": master.name,
        "phone": master.phone or master.contacts,
        "telegram": master.telegram,
        "instagram": master.instagram,
        "website": master.website,
        "contact_address": master.contact_address,
        "sphere": master.sphere,
        "contacts": _legacy_contacts(master),
        "socials": _legacy_socials(master),
        "work_hours": master.work_hours,
        "work_mode": master.work_mode,
        "work_address_default": master.work_address_default,
        "currency": master.currency,
        "timezone": master.timezone,
        "bonus_enabled": master.bonus_enabled,
        "bonus_rate": master.bonus_rate,
        "bonus_max_spend": master.bonus_max_spend,
        "bonus_birthday": master.bonus_birthday,
        "bonus_welcome": master.bonus_welcome,
        "gc_connected": master.gc_connected,
        "client_count": client_count,
    }


def _format_order(order: dict) -> dict:
    """Format a raw order dict for the dashboard response."""
    scheduled_at = order.get("scheduled_at", "")
    # Extract HH:MM from ISO datetime string (e.g. "2024-03-24 10:00:00")
    time_str = ""
    if scheduled_at:
        try:
            time_str = scheduled_at[11:16]  # "HH:MM"
        except Exception:
            time_str = ""

    client_name = order.get("client_name", "")
    # Abbreviate to "Имя Ф." format
    parts = client_name.split() if client_name else []
    if len(parts) >= 2:
        client_name_short = f"{parts[0]} {parts[1][0]}."
    else:
        client_name_short = client_name

    return {
        "id": order["id"],
        "time": time_str,
        "client_name": client_name_short,
        "services": order.get("services") or "",
        "amount": order.get("amount_total") or 0,
        "status": order.get("status", "new"),
    }


@router.get("/master/dashboard")
async def get_master_dashboard(
    master: Master = Depends(get_current_master)
):
    """Get aggregated dashboard data for the master."""
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Week: Monday to Sunday of current week
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Month: first to last day of current month
    month_start = today.replace(day=1)
    # Last day of month
    if today.month == 12:
        month_end = today.replace(day=31)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

    # Fetch all data concurrently-ish (sequential is fine for SQLite)
    today_orders_raw = await get_orders_by_date(master.id, today, all_statuses=False)
    tomorrow_orders_raw = await get_orders_by_date(master.id, tomorrow, all_statuses=False)
    week_report = await get_reports(master.id, week_start, week_end)
    month_report = await get_reports(master.id, month_start, month_end)
    pending_requests = await count_pending_requests(master.id)
    total_done = await count_done_orders(master.id)

    return {
        "master_name": master.name,
        "today_orders": [_format_order(o) for o in today_orders_raw],
        "tomorrow_orders": [_format_order(o) for o in tomorrow_orders_raw],
        "stats": {
            "week_revenue": week_report.get("revenue", 0),
            "month_revenue": month_report.get("revenue", 0),
            "week_orders": week_report.get("order_count", 0),
            "month_orders": month_report.get("order_count", 0),
            "total_clients": week_report.get("total_clients", 0),
            "pending_requests": pending_requests,
        },
        "total_done_orders": total_done,
        "onboarding_banner": {
            "show": master.onboarding_skipped_first_client and not master.onboarding_banner_shown,
            "skipped_first_client": master.onboarding_skipped_first_client,
            "banner_shown": master.onboarding_banner_shown,
        },
    }


@router.get("/master/invite-link")
async def get_master_invite_link(
    master: Master = Depends(get_current_master)
):
    """Return the invite link for the master's client bot."""
    bot_username = CLIENT_BOT_USERNAME or "client_bot"
    invite_link = f"https://t.me/{bot_username}?start=invite_{master.invite_token}"
    return {"invite_link": invite_link}
