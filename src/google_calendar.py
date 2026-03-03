"""Google Calendar integration module (stub for now)."""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


async def get_oauth_url(master_id: int) -> str:
    """Generate OAuth URL for Google Calendar authorization.

    TODO: Implement actual OAuth flow with google-auth-oauthlib
    """
    logger.info(f"[GC STUB] get_oauth_url called for master {master_id}")
    return "https://example.com/oauth/stub"


async def exchange_code(master_id: int, code: str) -> bool:
    """Exchange authorization code for credentials.

    TODO: Implement token exchange and save to masters.gc_credentials
    """
    logger.info(f"[GC STUB] exchange_code called for master {master_id}")
    return False


async def create_event(
    master_id: int,
    order: dict,
    client_name: str,
    client_phone: str,
    services: str,
    address: str,
    amount: int,
    scheduled_at: datetime
) -> Optional[str]:
    """Create calendar event for order.

    Returns event_id if successful, None otherwise.

    Event format:
    {
      "summary": f"{client_name} — {services}",
      "description": f"📞 {phone}\\n📍 {address}\\n🛠 {services}\\n💰 {amount} ₽",
      "start": {"dateTime": scheduled_at.isoformat(), "timeZone": "Europe/Moscow"},
      "end": {"dateTime": (scheduled_at + timedelta(hours=2)).isoformat(), "timeZone": "Europe/Moscow"}
    }

    TODO: Implement actual Google Calendar API call
    """
    logger.info(
        f"[GC STUB] create_event called for master {master_id}: "
        f"{client_name} at {scheduled_at}"
    )
    return None


async def update_event(
    master_id: int,
    event_id: str,
    new_dt: datetime
) -> bool:
    """Update event time in calendar.

    TODO: Implement actual Google Calendar API call
    """
    logger.info(
        f"[GC STUB] update_event called for master {master_id}: "
        f"event {event_id} -> {new_dt}"
    )
    return False


async def delete_event(master_id: int, event_id: str) -> bool:
    """Delete event from calendar.

    TODO: Implement actual Google Calendar API call
    """
    logger.info(
        f"[GC STUB] delete_event called for master {master_id}: "
        f"event {event_id}"
    )
    return False


async def get_calendar_account(master_id: int) -> Optional[str]:
    """Get connected Google account email.

    Returns email if connected, None otherwise.

    TODO: Implement actual credential check
    """
    logger.info(f"[GC STUB] get_calendar_account called for master {master_id}")
    return None


async def is_connected(master_id: int) -> bool:
    """Check if Google Calendar is connected for master."""
    account = await get_calendar_account(master_id)
    return account is not None
