"""Google Calendar integration module."""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from src.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI

logger = logging.getLogger(__name__)

# OAuth scopes
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",  # Events only (create, read, update, delete)
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

# Client config for OAuth flow
CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uris": [GOOGLE_REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


async def get_oauth_url(master_id: int) -> str:
    """Generate OAuth URL for Google Calendar authorization.

    state = str(master_id) for identifying master in callback.
    """
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI

    url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=str(master_id)
    )

    logger.info(f"Generated OAuth URL for master {master_id}")
    return url


async def exchange_code(master_id: int, code: str) -> Optional[str]:
    """Exchange authorization code for credentials.

    Saves credentials JSON to masters.gc_credentials.
    Returns email of connected account or None on error.
    """
    from src.database import save_gc_credentials

    try:
        flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
        flow.redirect_uri = GOOGLE_REDIRECT_URI

        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Save credentials to database
        creds_json = credentials.to_json()
        await save_gc_credentials(master_id, creds_json)

        # Get user email
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        email = user_info.get("email")

        logger.info(f"OAuth exchange successful for master {master_id}: {email}")
        return email

    except Exception as e:
        logger.error(f"OAuth exchange failed for master {master_id}: {e}")
        return None


async def get_credentials(master_id: int) -> Optional[Credentials]:
    """Load credentials from database.

    Automatically refreshes token if expired.
    Saves updated credentials back to database.
    """
    from src.database import get_gc_credentials, save_gc_credentials

    try:
        creds_json = await get_gc_credentials(master_id)
        if not creds_json:
            return None

        creds_data = json.loads(creds_json)
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save updated credentials
            await save_gc_credentials(master_id, creds.to_json())
            logger.info(f"Refreshed credentials for master {master_id}")

        return creds if creds.valid else None

    except Exception as e:
        logger.error(f"Failed to get credentials for master {master_id}: {e}")
        return None


async def create_event(
    master_id: int,
    client_name: str,
    client_phone: str,
    services: str,
    address: str,
    amount: int,
    scheduled_at: datetime
) -> Optional[str]:
    """Create calendar event for order.

    Returns event_id if successful, None otherwise.
    """
    credentials = await get_credentials(master_id)
    if not credentials:
        return None

    try:
        service = build("calendar", "v3", credentials=credentials)

        event = {
            "summary": f"{client_name} — {services}",
            "description": (
                f"📞 {client_phone or '—'}\n"
                f"📍 {address or '—'}\n"
                f"🛠 {services}\n"
                f"💰 {amount} ₽"
            ),
            "start": {
                "dateTime": scheduled_at.isoformat(),
                "timeZone": "Europe/Moscow"
            },
            "end": {
                "dateTime": (scheduled_at + timedelta(hours=2)).isoformat(),
                "timeZone": "Europe/Moscow"
            }
        }

        result = service.events().insert(calendarId="primary", body=event).execute()
        event_id = result.get("id")

        logger.info(f"Created calendar event {event_id} for master {master_id}")
        return event_id

    except Exception as e:
        logger.error(f"Failed to create event for master {master_id}: {e}")
        return None


async def update_event(master_id: int, event_id: str, new_dt: datetime) -> bool:
    """Update event time in calendar."""
    credentials = await get_credentials(master_id)
    if not credentials:
        return False

    try:
        service = build("calendar", "v3", credentials=credentials)

        # Get existing event
        event = service.events().get(calendarId="primary", eventId=event_id).execute()

        # Update times
        event["start"] = {
            "dateTime": new_dt.isoformat(),
            "timeZone": "Europe/Moscow"
        }
        event["end"] = {
            "dateTime": (new_dt + timedelta(hours=2)).isoformat(),
            "timeZone": "Europe/Moscow"
        }

        service.events().update(calendarId="primary", eventId=event_id, body=event).execute()

        logger.info(f"Updated calendar event {event_id} for master {master_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to update event {event_id} for master {master_id}: {e}")
        return False


async def delete_event(master_id: int, event_id: str) -> bool:
    """Delete event from calendar."""
    credentials = await get_credentials(master_id)
    if not credentials:
        return False

    try:
        service = build("calendar", "v3", credentials=credentials)
        service.events().delete(calendarId="primary", eventId=event_id).execute()

        logger.info(f"Deleted calendar event {event_id} for master {master_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete event {event_id} for master {master_id}: {e}")
        return False


async def get_calendar_account(master_id: int) -> Optional[str]:
    """Get connected Google account email."""
    credentials = await get_credentials(master_id)
    if not credentials:
        return None

    try:
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        return user_info.get("email")

    except Exception as e:
        logger.error(f"Failed to get account info for master {master_id}: {e}")
        return None


async def disconnect_calendar(master_id: int) -> bool:
    """Remove credentials from database."""
    from src.database import delete_gc_credentials

    try:
        await delete_gc_credentials(master_id)
        logger.info(f"Disconnected calendar for master {master_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to disconnect calendar for master {master_id}: {e}")
        return False


async def is_connected(master_id: int) -> bool:
    """Check if Google Calendar is connected for master."""
    account = await get_calendar_account(master_id)
    return account is not None
