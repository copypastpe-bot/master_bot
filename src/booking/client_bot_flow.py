"""Thin helper used by client_bot's /book command.

The client_bot already has the user's tg_id from the Telegram session, so we
skip the public anti-spam rate limit (the bot itself constrains how fast a
user can interact). Everything else mirrors the public POST /book path:
overlap-checked insert with source='telegram_bot' + master notification.

Returns a status dict that the caller (aiogram handler) turns into a user
message — that's why this lives in a separate module, away from aiogram
types, so it's trivially unit-testable.
"""
import logging
from typing import Optional

from src.database import (
    BookingConflictError,
    create_booking_with_overlap_check,
    get_client_by_tg_id,
    get_master_by_id,
    get_service_by_id,
    link_client_to_master,
)

logger = logging.getLogger(__name__)


async def book_via_bot(
    *,
    tg_id: int,
    master_id: int,
    service_id: int,
    scheduled_at: str,            # "YYYY-MM-DD HH:MM:SS"
    app,                           # FastAPI app (for master_bot in app.state)
) -> dict:
    """Attempt a self-booking on behalf of a Telegram-authenticated client.

    Status values:
      'ok'                       — order_id returned in the dict
      'client_not_found'         — no clients row has this tg_id
      'master_not_found'         — master_id doesn't resolve
      'self_booking_disabled'    — master toggled self-booking off
      'service_not_found'        — service_id missing or wrong master
      'slot_taken'               — overlap with an existing active order
    """
    client = await get_client_by_tg_id(tg_id)
    if client is None:
        return {"status": "client_not_found"}

    master = await get_master_by_id(master_id)
    if master is None:
        return {"status": "master_not_found"}
    if not master.self_booking_enabled:
        return {"status": "self_booking_disabled"}

    service = await get_service_by_id(service_id)
    if service is None or service.master_id != master_id:
        return {"status": "service_not_found"}

    await link_client_to_master(master_id, client.id)

    try:
        order_id = await create_booking_with_overlap_check(
            master_id=master_id,
            client_id=client.id,
            scheduled_at=scheduled_at,
            duration_minutes=service.duration_minutes,
            service_ids=[service.id],
            source="telegram_bot",
            amount_total=service.price or 0,
        )
    except BookingConflictError:
        return {"status": "slot_taken"}

    # Notify master via master_bot — best-effort.
    master_bot = getattr(getattr(app, "state", None), "master_bot", None)
    if master_bot:
        try:
            await master_bot.send_message(
                chat_id=master.tg_id,
                text=(
                    f"🆕 Новая запись (из бота)\n"
                    f"{client.name}, {client.phone or '—'}\n"
                    f"{service.name}, {scheduled_at}"
                ),
            )
        except Exception as e:
            logger.warning(f"master notify failed for order {order_id}: {e}")

    return {"status": "ok", "order_id": order_id}
