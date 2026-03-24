"""Master profile/dashboard endpoint."""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_master
from src.database import get_clients_paginated
from src.models import Master

router = APIRouter(tags=["master"])


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
        "phone": master.contacts,
        "sphere": master.sphere,
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
