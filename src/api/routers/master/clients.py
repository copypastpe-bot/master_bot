"""Master clients endpoints — list, card, edit, notes, bonuses."""

import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.dependencies import get_current_master
from src.database import (
    get_connection,
    get_last_client_address,
    get_client_with_stats,
    get_client_orders,
    get_client_bonus_log,
    update_client,
    update_client_note,
    manual_bonus_transaction,
)
from src.models import Master

logger = logging.getLogger(__name__)

router = APIRouter(tags=["master"])


# ---------------------------------------------------------------------------
# Internal helpers — enriched queries for list with stats
# ---------------------------------------------------------------------------

async def _search_clients_enriched(master_id: int, query: str) -> list[dict]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT
                c.id, c.name, c.phone, c.birthday,
                mc.bonus_balance,
                COALESCE(mc.total_spent, 0) as total_spent,
                (SELECT COUNT(*) FROM orders
                 WHERE master_id = ? AND client_id = c.id AND status = 'done') as order_count,
                (SELECT MAX(scheduled_at) FROM orders
                 WHERE master_id = ? AND client_id = c.id AND status = 'done') as last_visit
            FROM clients c
            JOIN master_clients mc ON c.id = mc.client_id
            WHERE mc.master_id = ?
              AND mc.is_archived = 0
              AND (LOWER(c.name) LIKE LOWER(?) OR c.phone LIKE ?)
            ORDER BY c.name
            LIMIT 50
            """,
            (master_id, master_id, master_id, f"%{query}%", f"%{query}%"),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def _get_clients_paginated_enriched(
    master_id: int, page: int, per_page: int
) -> tuple[list[dict], int]:
    conn = await get_connection()
    try:
        count_cur = await conn.execute(
            "SELECT COUNT(*) as cnt FROM master_clients WHERE master_id = ? AND is_archived = 0",
            (master_id,),
        )
        row = await count_cur.fetchone()
        total = row["cnt"] if row else 0

        offset = (page - 1) * per_page
        cursor = await conn.execute(
            """
            SELECT
                c.id, c.name, c.phone, c.birthday,
                mc.bonus_balance,
                COALESCE(mc.total_spent, 0) as total_spent,
                (SELECT COUNT(*) FROM orders
                 WHERE master_id = ? AND client_id = c.id AND status = 'done') as order_count,
                (SELECT MAX(scheduled_at) FROM orders
                 WHERE master_id = ? AND client_id = c.id AND status = 'done') as last_visit
            FROM clients c
            JOIN master_clients mc ON c.id = mc.client_id
            WHERE mc.master_id = ? AND mc.is_archived = 0
            ORDER BY c.name
            LIMIT ? OFFSET ?
            """,
            (master_id, master_id, master_id, per_page, offset),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows], total
    finally:
        await conn.close()


def _fmt_client_row(c: dict) -> dict:
    last_visit = c.get("last_visit")
    if last_visit and "T" in str(last_visit):
        last_visit = str(last_visit)[:10]
    return {
        "id": c["id"],
        "name": c.get("name") or "",
        "phone": c.get("phone") or "",
        "birthday": c.get("birthday"),
        "bonus_balance": c.get("bonus_balance") or 0,
        "total_spent": c.get("total_spent") or 0,
        "order_count": c.get("order_count") or 0,
        "last_visit": last_visit,
    }


# ---------------------------------------------------------------------------
# List / search — backward-compatible with V1 OrderCreate usage
# ---------------------------------------------------------------------------

@router.get("/master/clients")
async def list_master_clients(
    search: str = Query(default="", description="Search by name or phone"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=50),
    master: Master = Depends(get_current_master),
):
    """Paginated client list with stats. Also used by OrderCreate search."""
    if search.strip():
        clients = await _search_clients_enriched(master.id, search.strip())
        return {
            "clients": [_fmt_client_row(c) for c in clients],
            "total": len(clients),
            "page": 1,
            "pages": 1,
        }
    else:
        clients, total = await _get_clients_paginated_enriched(
            master.id, page=page, per_page=per_page
        )
        pages = max(1, math.ceil(total / per_page))
        return {
            "clients": [_fmt_client_row(c) for c in clients],
            "total": total,
            "page": page,
            "pages": pages,
        }


# ---------------------------------------------------------------------------
# Single client card
# ---------------------------------------------------------------------------

@router.get("/master/clients/{client_id}")
async def get_master_client(
    client_id: int,
    master: Master = Depends(get_current_master),
):
    """Full client card: profile + order history + bonus log."""
    client = await get_client_with_stats(master.id, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    orders_raw = await get_client_orders(master.id, client_id, limit=20)
    bonus_log_raw = await get_client_bonus_log(master.id, client_id, limit=30)

    orders = [
        {
            "id": o["id"],
            "scheduled_at": o.get("scheduled_at"),
            "services": o.get("services") or "",
            "amount_total": o.get("amount_total") or 0,
            "status": o.get("status"),
        }
        for o in orders_raw
    ]

    bonus_log = [
        {
            "date": (b.get("created_at") or "")[:10],
            "amount": b.get("amount") or 0,
            "type": b.get("type") or "accrual",
            "comment": b.get("comment") or "",
        }
        for b in bonus_log_raw
    ]

    # last_visit from stats or derive from orders
    last_visit = None
    done_orders = [o for o in orders_raw if o.get("status") == "done"]
    if done_orders:
        last_visit = str(done_orders[0].get("scheduled_at", ""))[:10]

    return {
        "id": client["id"],
        "name": client.get("name") or "",
        "phone": client.get("phone") or "",
        "birthday": client.get("birthday"),
        "bonus_balance": client.get("bonus_balance") or 0,
        "total_spent": client.get("total_spent") or 0,
        "order_count": client.get("order_count") or 0,
        "last_visit": last_visit,
        "note": client.get("note"),
        "orders": orders,
        "bonus_log": bonus_log,
    }


# ---------------------------------------------------------------------------
# Edit client
# ---------------------------------------------------------------------------

class ClientUpdateBody(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[str] = None


@router.put("/master/clients/{client_id}")
async def update_master_client(
    client_id: int,
    body: ClientUpdateBody,
    master: Master = Depends(get_current_master),
):
    """Update client profile fields."""
    client = await get_client_with_stats(master.id, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if kwargs:
        await update_client(client_id, **kwargs)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Note
# ---------------------------------------------------------------------------

class NoteBody(BaseModel):
    note: str


@router.put("/master/clients/{client_id}/note")
async def update_master_client_note(
    client_id: int,
    body: NoteBody,
    master: Master = Depends(get_current_master),
):
    """Update private note for a client."""
    client = await get_client_with_stats(master.id, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    await update_client_note(master.id, client_id, body.note)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Manual bonus transaction
# ---------------------------------------------------------------------------

class BonusBody(BaseModel):
    amount: int
    comment: str = ""


@router.post("/master/clients/{client_id}/bonus")
async def master_client_bonus(
    client_id: int,
    body: BonusBody,
    master: Master = Depends(get_current_master),
):
    """Manually accrue (positive) or deduct (negative) bonuses."""
    if body.amount == 0:
        raise HTTPException(status_code=422, detail="Amount must not be zero")

    client = await get_client_with_stats(master.id, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    await manual_bonus_transaction(master.id, client_id, body.amount, body.comment)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Last address — used by OrderCreate (V1 backward compat)
# ---------------------------------------------------------------------------

@router.get("/master/clients/{client_id}/last-address")
async def get_client_last_address(
    client_id: int,
    master: Master = Depends(get_current_master),
):
    """Last order address for this client (used in OrderCreate)."""
    address = await get_last_client_address(master.id, client_id)
    return {"address": address or ""}
