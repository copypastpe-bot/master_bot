"""Master registration endpoint."""

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.api.auth import validate_init_data, extract_tg_id
from src.config import MASTER_BOT_TOKEN, MASTER_BOT_USERNAME
from src.database import (
    activate_referral,
    create_master,
    get_all_categories,
    get_category_by_slug,
    get_master_by_tg_id,
    get_subscription_status,
    set_master_categories,
)
from src.utils import generate_invite_token

router = APIRouter(tags=["master-auth"])


class RegisterMasterRequest(BaseModel):
    name: str
    sphere: Optional[str] = None
    category_ids: Optional[list[int]] = None
    custom_names: Optional[dict[str, str]] = None
    contacts: Optional[str] = None
    work_hours: Optional[str] = None
    referral_code: Optional[str] = None


@router.post("/master/register")
async def register_master(
    body: RegisterMasterRequest,
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
):
    """
    Register a new master via Mini App.
    Returns 409 if master with this tg_id already exists.
    No dev-bypass — requires real Telegram initData.
    """
    if not x_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Init-Data header")

    validated = validate_init_data(x_init_data, MASTER_BOT_TOKEN)
    if not validated:
        raise HTTPException(status_code=401, detail="Invalid initData")

    tg_id = extract_tg_id(validated)
    if not tg_id:
        raise HTTPException(status_code=401, detail="No user data in initData")

    existing = await get_master_by_tg_id(tg_id)
    if existing:
        raise HTTPException(status_code=409, detail="Master already registered")

    if not body.name or not body.name.strip():
        raise HTTPException(status_code=422, detail="Name is required")

    normalized_custom_names: dict[int, str] = {}
    if body.category_ids:
        if not (1 <= len(body.category_ids) <= 3):
            raise HTTPException(status_code=422, detail="category_ids must contain 1-3 items")
        if len(set(body.category_ids)) != len(body.category_ids):
            raise HTTPException(status_code=422, detail="category_ids must be unique")
        categories = await get_all_categories()
        active_ids = {category["id"] for category in categories}
        if any(category_id not in active_ids for category_id in body.category_ids):
            raise HTTPException(status_code=422, detail="One or more categories do not exist")
        normalized_custom_names = {
            int(key): value.strip()
            for key, value in (body.custom_names or {}).items()
            if str(key).isdigit() and isinstance(value, str)
        }
        if any(not value or len(value) > 100 for value in normalized_custom_names.values()):
            raise HTTPException(status_code=422, detail="custom_names values must be 1-100 chars")
        other = await get_category_by_slug("other")
        other_id = other["id"] if other else None
        if other_id in body.category_ids and not normalized_custom_names.get(other_id):
            raise HTTPException(status_code=422, detail="Custom name is required for category 'other'")
        extra_custom_ids = set(normalized_custom_names.keys()) - set(body.category_ids)
        if extra_custom_ids:
            raise HTTPException(status_code=422, detail="custom_names contains ids outside category_ids")

    invite_token = generate_invite_token()
    master = await create_master(
        tg_id=tg_id,
        name=body.name.strip(),
        invite_token=invite_token,
        sphere=body.sphere or None,
        contacts=body.contacts or None,
        work_hours=body.work_hours or None,
    )
    if body.category_ids:
        await set_master_categories(master.id, body.category_ids, normalized_custom_names)
    await activate_referral(master.id, body.referral_code)
    subscription = await get_subscription_status(master.id)

    invite_link = f"https://t.me/{MASTER_BOT_USERNAME}?start={invite_token}"

    return {
        "id": master.id,
        "name": master.name,
        "invite_token": invite_token,
        "invite_link": invite_link,
        "referral_code": subscription["referral_code"],
        "role": "master",
    }
