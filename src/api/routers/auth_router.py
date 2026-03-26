"""Auth role detection endpoint."""

from typing import Optional
from fastapi import APIRouter, Header

from src.database import (
    get_master_by_tg_id,
    get_client_by_tg_id,
    get_master_client_by_client_tg_id,
    get_masters,
)
from src.api.auth import validate_init_data, extract_tg_id
from src.config import MASTER_BOT_TOKEN, CLIENT_BOT_TOKEN, APP_ENV

router = APIRouter(tags=["auth"])


@router.get("/auth/role")
async def get_role(
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data")
):
    """
    Determine the role of the Telegram user opening the Mini App.
    Returns {"role": "master"|"client"|"unknown", "id": int|None}.
    """
    # Dev bypass — return master role for the first master in DB
    if APP_ENV == "development" and x_init_data == "dev":
        masters = await get_masters()
        if masters:
            return {"role": "master", "id": masters[0].id}
        return {"role": "unknown", "id": None}

    if not x_init_data:
        return {"role": "unknown", "id": None}

    # Try master token first
    validated = validate_init_data(x_init_data, MASTER_BOT_TOKEN)
    if validated:
        tg_id = extract_tg_id(validated)
        if tg_id:
            master = await get_master_by_tg_id(tg_id)
            if master:
                return {"role": "master", "id": master.id}

    # Try client token
    validated = validate_init_data(x_init_data, CLIENT_BOT_TOKEN)
    if validated:
        tg_id = extract_tg_id(validated)
        if tg_id:
            client = await get_client_by_tg_id(tg_id)
            if client:
                mc = await get_master_client_by_client_tg_id(tg_id)
                if mc:
                    return {"role": "client", "id": client.id}

    return {"role": "unknown", "id": None}
