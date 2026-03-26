"""Master clients endpoints — search and last address."""

import logging

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_current_master
from src.database import search_clients, get_clients_paginated, get_last_client_address
from src.models import Master

logger = logging.getLogger(__name__)

router = APIRouter(tags=["master"])


@router.get("/master/clients")
async def search_master_clients(
    search: str = Query(default="", description="Search by name or phone"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    master: Master = Depends(get_current_master),
):
    """Search clients by name or phone, or return paginated list."""
    if search.strip():
        clients = await search_clients(master.id, search.strip())
        return {
            "clients": [
                {
                    "id": c["id"],
                    "name": c.get("name") or "",
                    "phone": c.get("phone") or "",
                    "bonus_balance": c.get("bonus_balance") or 0,
                }
                for c in clients
            ],
            "total": len(clients),
            "page": 1,
            "per_page": per_page,
        }
    else:
        clients, total = await get_clients_paginated(master.id, page=page, per_page=per_page)
        return {
            "clients": [
                {
                    "id": c["id"],
                    "name": c.get("name") or "",
                    "phone": c.get("phone") or "",
                    "bonus_balance": c.get("bonus_balance") or 0,
                }
                for c in clients
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        }


@router.get("/master/clients/{client_id}/last-address")
async def get_client_last_address(
    client_id: int,
    master: Master = Depends(get_current_master),
):
    """Get the address from the client's most recent order."""
    address = await get_last_client_address(master.id, client_id)
    return {"address": address or ""}
