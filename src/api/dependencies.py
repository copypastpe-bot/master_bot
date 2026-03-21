"""FastAPI dependencies for Mini App API."""

from fastapi import Header, HTTPException

from src.database import (
    get_client_by_tg_id,
    get_master_client_by_client_tg_id,
    get_master_by_id,
    get_masters,
)
from src.api.auth import validate_init_data, extract_tg_id
from src.config import CLIENT_BOT_TOKEN, APP_ENV
from src.models import Client, Master, MasterClient


async def _get_dev_client() -> tuple[Client, Master, MasterClient]:
    """Return first master's data for development testing."""
    masters = await get_masters()
    if not masters:
        raise HTTPException(status_code=404, detail="No masters in DB for dev mode")
    m = masters[0]
    # Build Master dataclass from dict — only include fields that exist in both
    master_fields = Master.__dataclass_fields__.keys()
    master = Master(**{k: m[k] for k in master_fields if k in m})
    fake_client = Client(
        id=0,
        name="Dev User",
        tg_id=master.tg_id,
        phone="+79991234567",
        birthday=None,
    )
    fake_master_client = MasterClient(
        id=0,
        master_id=master.id,
        client_id=0,
        bonus_balance=450,
        note=None,
    )
    return fake_client, master, fake_master_client


async def get_current_client(
    x_init_data: str = Header(..., alias="X-Init-Data")
) -> tuple[Client, Master, MasterClient]:
    """
    Dependency - validate initData and return (client, master, master_client).
    In development mode with X-Init-Data: "dev" — returns first DB client without HMAC check.
    Raises 401 if invalid, 404 if client not found in DB.
    """
    # Dev bypass
    if APP_ENV == "development" and x_init_data == "dev":
        return await _get_dev_client()

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
