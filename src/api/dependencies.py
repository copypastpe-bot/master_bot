"""FastAPI dependencies for Mini App API."""

from fastapi import Header, HTTPException

from src.database import (
    get_client_by_tg_id,
    get_master_client_by_client_tg_id,
    get_master_by_id,
)
from src.api.auth import validate_init_data, extract_tg_id
from src.config import CLIENT_BOT_TOKEN
from src.models import Client, Master, MasterClient


async def get_current_client(
    x_init_data: str = Header(..., alias="X-Init-Data")
) -> tuple[Client, Master, MasterClient]:
    """
    Dependency - validate initData and return (client, master, master_client).
    Raises 401 if invalid, 404 if client not found in DB.
    """
    validated = validate_init_data(x_init_data, CLIENT_BOT_TOKEN)
    if not validated:
        raise HTTPException(status_code=401, detail="Invalid initData")

    tg_id = extract_tg_id(validated)
    if not tg_id:
        raise HTTPException(status_code=401, detail="No user data")

    client = await get_client_by_tg_id(tg_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not registered")

    master_client = await get_master_client_by_client_tg_id(tg_id)
    if not master_client:
        raise HTTPException(status_code=404, detail="Master not linked")

    master = await get_master_by_id(master_client.master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")

    return client, master, master_client
