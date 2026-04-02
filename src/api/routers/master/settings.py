"""Master settings endpoints — profile, timezone, currency, bonus settings, services."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from src.api.dependencies import get_current_master
from src.config import CLIENT_BOT_USERNAME
from src.database import (
    get_services,
    get_archived_services,
    get_service_by_id,
    create_service,
    update_service,
    archive_service,
    restore_service,
    update_master,
    update_master_bonus_setting,
)
from src.models import Master

logger = logging.getLogger(__name__)

router = APIRouter(tags=["master-settings"])

ALLOWED_TIMEZONES = {
    "Europe/Moscow", "Europe/Kaliningrad", "Asia/Yekaterinburg",
    "Asia/Novosibirsk", "Asia/Krasnoyarsk", "Asia/Irkutsk",
    "Asia/Vladivostok", "Asia/Kamchatka", "Europe/Minsk",
    "Asia/Almaty", "Europe/Kiev", "Europe/Istanbul",
}

ALLOWED_CURRENCIES = {"RUB", "UAH", "BYN", "KZT", "USD", "EUR", "TRY", "GEL", "UZS"}


# =============================================================================
# Profile
# =============================================================================

class ProfileUpdateBody(BaseModel):
    name: Optional[str] = None
    sphere: Optional[str] = None
    contacts: Optional[str] = None
    socials: Optional[str] = None
    work_hours: Optional[str] = None
    onboarding_banner_shown: Optional[bool] = None
    onboarding_skipped_first_client: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError("name cannot be empty")
        if v is not None and len(v) > 100:
            raise ValueError("name max 100 chars")
        return v


@router.put("/master/profile")
async def update_master_profile(
    body: ProfileUpdateBody,
    master: Master = Depends(get_current_master),
):
    """Update master profile fields."""
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if kwargs:
        await update_master(master.id, **kwargs)
    return {"ok": True}


# =============================================================================
# Timezone
# =============================================================================

class TimezoneBody(BaseModel):
    timezone: str

    @field_validator("timezone")
    @classmethod
    def tz_allowed(cls, v):
        if v not in ALLOWED_TIMEZONES:
            raise ValueError(f"Unknown timezone: {v}")
        return v


@router.put("/master/timezone")
async def update_master_timezone(
    body: TimezoneBody,
    master: Master = Depends(get_current_master),
):
    await update_master(master.id, timezone=body.timezone)
    return {"ok": True}


# =============================================================================
# Currency
# =============================================================================

class CurrencyBody(BaseModel):
    currency: str

    @field_validator("currency")
    @classmethod
    def cur_allowed(cls, v):
        if v not in ALLOWED_CURRENCIES:
            raise ValueError(f"Unknown currency: {v}")
        return v


@router.put("/master/currency")
async def update_master_currency(
    body: CurrencyBody,
    master: Master = Depends(get_current_master),
):
    await update_master(master.id, currency=body.currency)
    return {"ok": True}


# =============================================================================
# Invite link
# =============================================================================

@router.get("/master/invite")
async def get_master_invite(
    master: Master = Depends(get_current_master),
):
    """Return invite link and token for the master."""
    bot_username = CLIENT_BOT_USERNAME or "client_bot"
    invite_link = f"https://t.me/{bot_username}?start=invite_{master.invite_token}"
    return {
        "invite_link": invite_link,
        "invite_token": master.invite_token,
    }


# =============================================================================
# Bonus settings
# =============================================================================

@router.get("/master/bonus-settings")
async def get_bonus_settings(
    master: Master = Depends(get_current_master),
):
    return {
        "bonus_enabled": master.bonus_enabled,
        "bonus_rate": master.bonus_rate,
        "bonus_max_spend": master.bonus_max_spend,
        "bonus_birthday": master.bonus_birthday,
        "bonus_welcome": master.bonus_welcome,
        "welcome_message": master.welcome_message,
        "birthday_message": master.birthday_message,
    }


class BonusSettingsBody(BaseModel):
    bonus_enabled: Optional[bool] = None
    bonus_rate: Optional[float] = None
    bonus_max_spend: Optional[float] = None
    bonus_birthday: Optional[int] = None
    bonus_welcome: Optional[int] = None

    @field_validator("bonus_rate")
    @classmethod
    def rate_range(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("bonus_rate must be 0-100")
        return v

    @field_validator("bonus_max_spend")
    @classmethod
    def max_spend_range(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("bonus_max_spend must be 0-100")
        return v

    @field_validator("bonus_birthday", "bonus_welcome")
    @classmethod
    def non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("value must be >= 0")
        return v


@router.put("/master/bonus-settings")
async def update_bonus_settings(
    body: BonusSettingsBody,
    master: Master = Depends(get_current_master),
):
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if kwargs:
        await update_master(master.id, **kwargs)
    return {"ok": True}


# =============================================================================
# Services — unified endpoint (backward compat + V2 settings)
# =============================================================================

@router.get("/master/services")
async def get_master_services_all(
    master: Master = Depends(get_current_master),
):
    """
    Return active and archived services.

    Response includes both:
      - `services`: active only (backward compat for V1 OrderCreate)
      - `active`: active services (V2 settings)
      - `archived`: archived services (V2 settings)
    """
    active = await get_services(master.id, active_only=True)
    archived = await get_archived_services(master.id)

    def _fmt(s):
        return {
            "id": s.id,
            "name": s.name,
            "price": s.price or 0,
            "description": s.description or "",
        }

    active_list = [_fmt(s) for s in active]
    archived_list = [_fmt(s) for s in archived]

    return {
        "services": active_list,          # V1 backward compat
        "active": active_list,            # V2 settings
        "archived": archived_list,        # V2 settings
    }


class ServiceCreateBody(BaseModel):
    name: str
    price: int
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("name required")
        return v

    @field_validator("price")
    @classmethod
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError("price must be > 0")
        return v


@router.post("/master/services")
async def create_master_service(
    body: ServiceCreateBody,
    master: Master = Depends(get_current_master),
):
    service = await create_service(
        master.id, body.name, body.price, body.description
    )
    return {
        "id": service.id,
        "name": service.name,
        "price": service.price or 0,
        "description": service.description or "",
    }


class ServiceUpdateBody(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None
    description: Optional[str] = None

    @field_validator("price")
    @classmethod
    def price_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("price must be > 0")
        return v


@router.put("/master/services/{service_id}")
async def update_master_service(
    service_id: int,
    body: ServiceUpdateBody,
    master: Master = Depends(get_current_master),
):
    service = await get_service_by_id(service_id)
    if not service or service.master_id != master.id:
        raise HTTPException(status_code=404, detail="Service not found")

    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if kwargs:
        await update_service(service_id, **kwargs)
    return {"ok": True}


@router.put("/master/services/{service_id}/archive")
async def archive_master_service(
    service_id: int,
    master: Master = Depends(get_current_master),
):
    service = await get_service_by_id(service_id)
    if not service or service.master_id != master.id:
        raise HTTPException(status_code=404, detail="Service not found")
    await archive_service(service_id)
    return {"ok": True}


@router.put("/master/services/{service_id}/restore")
async def restore_master_service(
    service_id: int,
    master: Master = Depends(get_current_master),
):
    service = await get_service_by_id(service_id)
    if not service or service.master_id != master.id:
        raise HTTPException(status_code=404, detail="Service not found")
    await restore_service(service_id)
    return {"ok": True}
