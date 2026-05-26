"""Public (unauthenticated) booking endpoints.

These are the first endpoints in the project that anyone on the open
internet can call. Two surfaces:

  GET  /api/public/{slug}/slots?service_id=N&date=YYYY-MM-DD
       Returns the list of free 'HH:MM' start times for that date.

  POST /api/public/book
       Creates a confirmed booking and notifies the master via master_bot.

Defence in depth:
  - Per-IP rate-limit on POST (5/h) — see ratelimit.py.
  - Server-side phone validation via `phonenumbers` (already in requirements).
  - Overlap protection at the DB layer (BEGIN IMMEDIATE + WAL from sprint 1)
    via create_booking_with_overlap_check.
  - Slug currently resolves to the master's invite_token (unique per master);
    when a dedicated public slug appears in promo_pages, swap _load_master().
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.api.ratelimit import public_book_limiter
from src.booking.slot_generator import generate_slots
from src.config import MINIAPP_URL
from src.database import (
    BookingConflictError,
    create_booking_with_overlap_check,
    create_client,
    get_client_by_phone,
    get_client_by_tg_id,
    get_connection,
    get_master_by_invite_token,
    get_master_schedule_exceptions,
    get_master_schedule_weekly,
    get_service_by_id,
    link_client_to_master,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["public"])


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _normalize_phone(raw: str) -> Optional[str]:
    """Return E.164 phone or None if the input doesn't parse to a valid RU number.
    Default region is RU since the pilot is Moscow-only — extend later for
    other countries by reading master.country or similar."""
    try:
        import phonenumbers
        parsed = phonenumbers.parse(raw, "RU")
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        return None


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _load_master(slug: str):
    """Resolve a public slug to a self-booking-enabled master.

    Today: slug == master.invite_token (the existing minisite URL).
    Future: prefer promo_pages.slug when one is set.

    Raises 404 if not found, 403 if self-booking is disabled.
    """
    m = await get_master_by_invite_token(slug)
    if not m:
        raise HTTPException(status_code=404, detail="Master not found")
    if not m.self_booking_enabled:
        raise HTTPException(status_code=403, detail="Self-booking disabled for this master")
    return m


async def _existing_bookings_for_date(master_id: int, date: str) -> list[tuple[str, int]]:
    """Return [(start_HHMM, duration_minutes)] of active orders on date.

    Active = status not in (cancelled, done). 'done' is excluded because a
    finished slot in the past doesn't block future booking math; concurrent
    booking protection lives in create_booking_with_overlap_check."""
    conn = await get_connection()
    try:
        cur = await conn.execute(
            """
            SELECT scheduled_at, duration_minutes FROM orders
            WHERE master_id = ?
              AND date(scheduled_at) = ?
              AND status NOT IN ('cancelled', 'done')
            """,
            (master_id, date),
        )
        out = []
        for row in await cur.fetchall():
            sched = row["scheduled_at"] or ""
            # ISO can use 'T' or ' ' separator; take the time portion.
            t = sched.split("T")[-1].split(" ")[-1][:5]
            if t:
                out.append((t, row["duration_minutes"] or 60))
        return out
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/public/{slug}/slots")
async def get_public_slots(slug: str, service_id: int, date: str):
    """List available start times for a service on a date."""
    master = await _load_master(slug)
    service = await get_service_by_id(service_id)
    if not service or service.master_id != master.id:
        raise HTTPException(status_code=404, detail="Service not found")

    target = datetime.fromisoformat(date)
    weekday = target.weekday()

    weekly_rows = await get_master_schedule_weekly(master.id)
    weekly_intervals = [
        (r["start_time"], r["end_time"]) for r in weekly_rows if r["weekday"] == weekday
    ]

    exc_rows = await get_master_schedule_exceptions(master.id, date)
    exception = None
    if exc_rows:
        e = exc_rows[0]
        exception = {"kind": e["kind"], "start": e["start_time"], "end": e["end_time"]}

    existing = await _existing_bookings_for_date(master.id, date)
    today_iso = datetime.now().date().isoformat()
    slots = generate_slots(
        weekly_intervals=weekly_intervals,
        exception=exception,
        duration_minutes=service.duration_minutes,
        existing_bookings=existing,
        now=datetime.now() if date == today_iso else None,
        target_date=date,
    )
    return {"slots": slots}


class PublicBookBody(BaseModel):
    slug: str
    service_id: int
    date: str
    start: str
    name: str = Field(min_length=1, max_length=80)
    phone: str
    tg_username: Optional[str] = None
    tg_id: Optional[int] = None


@router.post("/public/book")
async def public_book(request: Request, body: PublicBookBody):
    """Create a confirmed booking from public input."""
    ip = _client_ip(request)
    if not public_book_limiter.is_allowed(f"ip:{ip}"):
        raise HTTPException(status_code=429, detail="Too many bookings from this IP")

    master = await _load_master(body.slug)
    service = await get_service_by_id(body.service_id)
    if not service or service.master_id != master.id:
        raise HTTPException(status_code=404, detail="Service not found")

    phone = _normalize_phone(body.phone)
    if phone is None:
        raise HTTPException(status_code=422, detail="Invalid phone number")

    # Upsert client. tg_id first (most reliable), then phone, then create.
    client = None
    if body.tg_id is not None:
        client = await get_client_by_tg_id(body.tg_id)
    if client is None:
        client = await get_client_by_phone(phone)
    if client is None:
        client = await create_client(
            name=body.name, phone=phone, tg_id=body.tg_id,
        )
    client_id = client.id

    await link_client_to_master(master.id, client_id)

    scheduled_at = f"{body.date} {body.start}:00"
    try:
        order_id = await create_booking_with_overlap_check(
            master_id=master.id,
            client_id=client_id,
            scheduled_at=scheduled_at,
            duration_minutes=service.duration_minutes,
            service_ids=[service.id],
            source="public",
            amount_total=service.price or 0,
        )
    except BookingConflictError:
        raise HTTPException(status_code=409, detail="Slot already taken")

    # Read back the cancel_token (uuid stamped by create_booking_with_overlap_check).
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "SELECT cancel_token FROM orders WHERE id = ?", (order_id,)
        )
        cancel_token = (await cur.fetchone())["cancel_token"]
    finally:
        await conn.close()

    # Master notification — best-effort, never blocks the response.
    master_bot = getattr(request.app.state, "master_bot", None)
    if master_bot:
        try:
            await master_bot.send_message(
                chat_id=master.tg_id,
                text=(
                    f"🆕 Новая запись\n"
                    f"{body.name}, {phone}\n"
                    f"{service.name}, {body.date} {body.start}"
                ),
            )
        except Exception as e:
            logger.warning(f"master notify failed for order {order_id}: {e}")

    # Build the cancellation URL. MINIAPP_URL is the Mini App host;
    # /b/{token} is served by the public landing router.
    parsed_host = MINIAPP_URL.split("//", 1)[-1].split("/", 1)[0]
    scheme = MINIAPP_URL.split("://", 1)[0] if "://" in MINIAPP_URL else "https"
    cancel_url = f"{scheme}://{parsed_host}/b/{cancel_token}"

    return JSONResponse(
        status_code=201,
        content={
            "order_id": order_id,
            "cancel_token": cancel_token,
            "cancel_url": cancel_url,
        },
    )
