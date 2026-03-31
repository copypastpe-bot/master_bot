"""Client multi-master endpoints: list masters, link to new master."""

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.api.auth import validate_init_data, extract_tg_id
from src.config import CLIENT_BOT_TOKEN, APP_ENV
from src.database import (
    get_client_by_tg_id,
    get_master_by_invite_token,
    get_all_client_masters_by_tg_id,
    link_existing_client_to_master,
    accrue_welcome_bonus,
    get_masters,
)

router = APIRouter(tags=["client-masters"])


async def _resolve_tg_id(x_init_data: Optional[str]) -> int:
    """Validate initData and return tg_id. Raises 401 on failure."""
    if not x_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Init-Data header")
    if APP_ENV == "development" and x_init_data == "dev":
        return 999999999
    validated = validate_init_data(x_init_data, CLIENT_BOT_TOKEN)
    if not validated:
        raise HTTPException(status_code=401, detail="Invalid initData")
    tg_id = extract_tg_id(validated)
    if not tg_id:
        raise HTTPException(status_code=401, detail="No user data")
    return tg_id


@router.get("/client/masters")
async def get_client_masters_list(
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    """Return all masters linked to this client."""
    tg_id = await _resolve_tg_id(x_init_data)
    masters = await get_all_client_masters_by_tg_id(tg_id)
    return {"masters": masters, "count": len(masters)}


class LinkMasterRequest(BaseModel):
    invite_token: str


@router.post("/client/link")
async def link_to_master(
    body: LinkMasterRequest,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    """Link this client to a new master via invite token."""
    tg_id = await _resolve_tg_id(x_init_data)

    client = await get_client_by_tg_id(tg_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not registered")

    master = await get_master_by_invite_token(body.invite_token)
    if not master:
        raise HTTPException(status_code=404, detail="Invite token not found")

    linked = await link_existing_client_to_master(client.id, master.id)
    if not linked:
        raise HTTPException(status_code=409, detail="Already linked to this master")

    # Accrue welcome bonus if configured (idempotent — won't double-accrue)
    await accrue_welcome_bonus(master.id, client.id)

    # Return master info with fresh bonus balance
    masters = await get_all_client_masters_by_tg_id(tg_id)
    entry = next((m for m in masters if m["master_id"] == master.id), {})

    return {
        "master_id": master.id,
        "name": master.name,
        "sphere": master.sphere,
        "bonus_balance": entry.get("bonus_balance", 0),
    }
