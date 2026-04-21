"""Master clients endpoints — list, card, edit, notes, bonuses."""

import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from src.api.dependencies import get_current_master
from src.api.ratelimit import write_limiter
from src.database import (
    get_connection,
    get_last_client_address,
    get_client_addresses,
    save_client_address,
    get_client_with_stats,
    get_client_orders,
    get_client_bonus_log,
    update_client,
    update_client_note,
    manual_bonus_transaction,
    get_client_by_phone,
    create_client,
    link_client_to_master,
    restore_client,
)
from src.models import Master
from src.utils import normalize_phone, parse_date

logger = logging.getLogger(__name__)

router = APIRouter(tags=["master"])


def _normalize_birthday(raw: Optional[str]) -> Optional[str]:
    """Normalize birthday to YYYY-MM-DD. Accepts ISO and DD.MM.YYYY formats.
    Returns None if raw is empty/unparseable, raises HTTPException on future date."""
    if not raw:
        return None
    from datetime import date as date_cls
    # Try ISO format first (from HTML date input per spec)
    try:
        bday = date_cls.fromisoformat(raw)
    except ValueError:
        # Fall back to DD.MM.YYYY (Telegram WebView locale format)
        bday = parse_date(raw)
    if bday is None:
        raise HTTPException(422, "Неверный формат даты рождения")
    if bday > date_cls.today():
        raise HTTPException(422, "Дата рождения не может быть в будущем")
    return bday.isoformat()


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
    if "birthday" in kwargs:
        kwargs["birthday"] = _normalize_birthday(kwargs["birthday"])
        if kwargs["birthday"] is None:
            del kwargs["birthday"]
    if kwargs:
        await update_client(client_id, **kwargs)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Note
# ---------------------------------------------------------------------------

class NoteBody(BaseModel):
    note: str = Field(max_length=2000)


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
    amount: int = Field(ge=-100_000, le=100_000)
    comment: str = Field(default="", max_length=500)


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
# Create client
# ---------------------------------------------------------------------------

class ClientCreateRequest(BaseModel):
    name: str
    phone: str
    birthday: Optional[str] = None


@router.post("/master/clients", status_code=201)
async def create_master_client_endpoint(
    body: ClientCreateRequest,
    request: Request,
    master: Master = Depends(get_current_master),
    _: None = Depends(write_limiter.make_dependency()),
):
    """Create or link a client. Handles duplicate phone scenarios."""
    name = body.name.strip()
    if not name or len(name) > 100:
        raise HTTPException(422, "name must be 1-100 characters")

    normalized_phone = normalize_phone(body.phone)
    if not normalized_phone:
        raise HTTPException(422, "invalid phone number")

    birthday = _normalize_birthday(body.birthday)

    existing = await get_client_by_phone(normalized_phone)

    if existing:
        # Check master-client link including is_archived (not in MasterClient dataclass)
        conn = await get_connection()
        try:
            cursor = await conn.execute(
                "SELECT is_archived FROM master_clients WHERE master_id = ? AND client_id = ?",
                (master.id, existing.id),
            )
            mc_row = await cursor.fetchone()
        finally:
            await conn.close()

        if mc_row:
            if not mc_row["is_archived"]:
                raise HTTPException(
                    409,
                    detail={"error": "client_exists", "archived": False},
                )
            else:
                raise HTTPException(
                    409,
                    detail={
                        "error": "client_archived",
                        "archived": True,
                        "client_id": existing.id,
                        "name": existing.name,
                    },
                )
        # Client exists globally but not linked to this master — link them
        await link_client_to_master(master.id, existing.id)
        updates = {}
        if name and name != existing.name:
            updates["name"] = name
        if birthday and birthday != existing.birthday:
            updates["birthday"] = birthday
        if updates:
            await update_client(existing.id, **updates)
        client = existing
        is_new = False
    else:
        client = await create_client(
            name=name,
            tg_id=None,
            phone=normalized_phone,
            birthday=birthday,
        )
        await link_client_to_master(master.id, client.id)
        is_new = True

    return {
        "id": client.id,
        "name": name if is_new else (client.name or name),
        "phone": normalized_phone,
        "birthday": birthday or client.birthday,
        "bonus_balance": 0,
        "is_new": is_new,
    }


# ---------------------------------------------------------------------------
# Client addresses
# ---------------------------------------------------------------------------

class ClientAddressBody(BaseModel):
    address: str = Field(max_length=500)
    label: Optional[str] = Field(default=None, max_length=100)
    make_default: bool = False


@router.get("/master/clients/{client_id}/addresses")
async def get_master_client_addresses(
    client_id: int,
    master: Master = Depends(get_current_master),
):
    """Saved addresses for this client in current master's workspace."""
    client = await get_client_with_stats(master.id, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    items = await get_client_addresses(master.id, client_id)
    return {"addresses": items}


@router.post("/master/clients/{client_id}/addresses")
async def create_master_client_address(
    client_id: int,
    body: ClientAddressBody,
    master: Master = Depends(get_current_master),
):
    """Create or update saved client address."""
    client = await get_client_with_stats(master.id, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    try:
        item = await save_client_address(
            master_id=master.id,
            client_id=client_id,
            address=body.address,
            label=body.label,
            make_default=body.make_default,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return item


# ---------------------------------------------------------------------------
# Restore archived client
# ---------------------------------------------------------------------------

@router.post("/master/clients/{client_id}/restore")
async def restore_master_client(
    client_id: int,
    master: Master = Depends(get_current_master),
):
    """Restore archived client."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT is_archived FROM master_clients WHERE master_id = ? AND client_id = ?",
            (master.id, client_id),
        )
        mc_row = await cursor.fetchone()
    finally:
        await conn.close()

    if not mc_row:
        raise HTTPException(404, "client not found")
    if not mc_row["is_archived"]:
        raise HTTPException(409, "client is not archived")

    await restore_client(master.id, client_id)

    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT id, name, phone, birthday FROM clients WHERE id = ?",
            (client_id,),
        )
        row = await cursor.fetchone()
    finally:
        await conn.close()

    if not row:
        raise HTTPException(404, "client not found")

    return {
        "id": row["id"],
        "name": row["name"] or "",
        "phone": row["phone"] or "",
        "birthday": row["birthday"],
        "bonus_balance": 0,
        "is_new": False,
    }


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
