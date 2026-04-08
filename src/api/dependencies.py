"""FastAPI dependencies for Mini App API."""

from typing import Optional, Tuple
from fastapi import Header, HTTPException, Query, Request

from src.database import (
    get_client_by_tg_id,
    get_master_client_by_client_tg_id,
    get_master_by_id,
    get_master_by_tg_id,
    get_masters,
    get_master_client,
    get_all_client_masters_by_tg_id,
    activate_trial,
    get_subscription_brief,
)
from src.api.auth import validate_init_data, extract_tg_id
from src.config import CLIENT_BOT_TOKEN, MASTER_BOT_TOKEN, APP_ENV
from src.models import Client, Master, MasterClient


class SubscriptionRequiredError(Exception):
    """Raised when request requires active subscription."""

    def __init__(self, payload: dict):
        super().__init__("subscription_required")
        self.payload = payload


def _is_blocked_write_without_subscription(request: Request) -> bool:
    """Return True for endpoints that should be blocked when subscription expired."""
    method = request.method.upper()
    path = request.url.path

    if method == "POST" and path == "/api/master/orders":
        return True
    if method == "POST" and path == "/api/master/clients":
        return True
    if method in {"POST", "PUT", "PATCH", "DELETE"} and path.startswith("/api/master/broadcast/"):
        return True
    if method == "POST" and path == "/api/master/promos":
        return True
    if method in {"PUT", "PATCH", "DELETE"} and path.startswith("/api/master/promos/"):
        return True
    return False


async def _guard_master_subscription(master: Master, request: Request) -> None:
    """Auto-activate trial and guard selected write endpoints when expired."""
    if not request.url.path.startswith("/api/master/"):
        return

    if master.subscription_until is None and not master.trial_used:
        await activate_trial(master.id)

    status = await get_subscription_brief(master.id)
    if status["is_active"]:
        return

    if not _is_blocked_write_without_subscription(request):
        return

    subscription_until = status["subscription_until"]
    raise SubscriptionRequiredError({
        "error": "subscription_required",
        "subscription_until": subscription_until.isoformat() if subscription_until else None,
        "days_left": status["days_left"],
    })


async def _get_dev_client() -> Tuple[Client, Master, MasterClient]:
    """Return first master's data for development testing."""
    masters = await get_masters()
    if not masters:
        raise HTTPException(status_code=404, detail="No masters in DB for dev mode")
    master = masters[0]
    fake_client = Client(
        id=0,
        tg_id=999999999,
        name="Dev User",
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
    master_id: Optional[int] = Query(None),
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
) -> Tuple[Client, Master, MasterClient]:
    """
    Dependency - validate initData and return (client, master, master_client).

    Master determined by:
    1. ?master_id=X query param (explicit)
    2. If client has only 1 master → use that one (backward compat)
    3. If client has multiple masters and no master_id → HTTP 400

    In development mode with X-Init-Data: "dev" — returns first DB client without HMAC check.
    Raises 401 if invalid, 404 if client not found.
    """
    if not x_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Init-Data header")

    # Dev bypass — unchanged behaviour
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

    masters = await get_all_client_masters_by_tg_id(tg_id)
    if not masters:
        raise HTTPException(status_code=404, detail="Not linked to any master")

    if master_id is not None:
        entry = next((m for m in masters if m["master_id"] == master_id), None)
        if entry is None:
            raise HTTPException(status_code=403, detail="Not linked to this master")
        chosen_master_id = master_id
    elif len(masters) == 1:
        chosen_master_id = masters[0]["master_id"]
    else:
        raise HTTPException(
            status_code=400,
            detail="Укажите master_id: у вас несколько мастеров",
        )

    master = await get_master_by_id(chosen_master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")

    master_client = await get_master_client(chosen_master_id, client.id)
    if not master_client:
        raise HTTPException(status_code=404, detail="Master-client link not found")

    return client, master, master_client


async def get_current_master(
    request: Request,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data")
) -> Master:
    """
    Dependency - validate initData and return Master.
    In development mode with X-Init-Data: "dev" — returns first DB master without HMAC check.
    Raises 401 if invalid, 403 if not a master.
    """
    if not x_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Init-Data header")

    # Dev bypass
    if APP_ENV == "development" and x_init_data == "dev":
        masters = await get_masters()
        if not masters:
            raise HTTPException(status_code=404, detail="No masters in DB for dev mode")
        master = masters[0]
        await _guard_master_subscription(master, request)
        return master

    validated = validate_init_data(x_init_data, MASTER_BOT_TOKEN)
    if not validated:
        raise HTTPException(status_code=401, detail="Invalid initData")

    tg_id = extract_tg_id(validated)
    if not tg_id:
        raise HTTPException(status_code=401, detail="No user data")

    master = await get_master_by_tg_id(tg_id)
    if not master:
        raise HTTPException(status_code=403, detail="Not a master")

    await _guard_master_subscription(master, request)
    return master
