"""Master registration endpoint."""

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.api.auth import validate_init_data, extract_tg_id
from src.config import MASTER_BOT_TOKEN, MASTER_BOT_USERNAME
from src.database import get_master_by_tg_id, create_master, activate_referral, get_subscription_status
from src.utils import generate_invite_token

router = APIRouter(tags=["master-auth"])


class RegisterMasterRequest(BaseModel):
    name: str
    sphere: Optional[str] = None
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

    invite_token = generate_invite_token()
    master = await create_master(
        tg_id=tg_id,
        name=body.name.strip(),
        invite_token=invite_token,
        sphere=body.sphere or None,
        contacts=body.contacts or None,
        work_hours=body.work_hours or None,
    )
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
