"""Master settings endpoints — profile, timezone, currency, bonus settings, services."""

import json
import logging
import re
import secrets
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from src.api.dependencies import get_current_master
from src.config import CLIENT_BOT_USERNAME
from src import google_calendar
from src.database import (
    add_portfolio_photo,
    delete_portfolio_photo,
    get_master_by_id,
    get_master_portfolio,
    get_services,
    get_archived_services,
    get_service_by_id,
    create_service,
    update_service,
    archive_service,
    restore_service,
    update_master,
)
from src.models import Master
from src.utils import normalize_phone

logger = logging.getLogger(__name__)

router = APIRouter(tags=["master-settings"])
_master_bot = None


def set_master_bot(bot) -> None:
    global _master_bot
    _master_bot = bot

ALLOWED_TIMEZONES = {
    "Europe/London", "Europe/Lisbon", "Europe/Madrid", "Europe/Paris",
    "Europe/Berlin", "Europe/Rome", "Europe/Amsterdam", "Europe/Brussels",
    "Europe/Vienna", "Europe/Prague", "Europe/Warsaw", "Europe/Belgrade",
    "Europe/Athens", "Europe/Bucharest", "Europe/Helsinki", "Europe/Riga",
    "Europe/Vilnius", "Europe/Tallinn", "Asia/Jerusalem",
    "Europe/Moscow", "Europe/Kaliningrad", "Asia/Yekaterinburg",
    "Asia/Novosibirsk", "Asia/Krasnoyarsk", "Asia/Irkutsk",
    "Asia/Vladivostok", "Asia/Kamchatka", "Europe/Minsk",
    "Asia/Almaty", "Europe/Kiev", "Europe/Istanbul",
}

ALLOWED_CURRENCIES = {"RUB", "EUR", "ILS", "UAH", "BYN", "KZT", "USD", "TRY", "GEL", "UZS"}
TELEGRAM_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")
INSTAGRAM_USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")

BONUS_MEDIA_DIR = Path("/app/data/bonus_media")
MAX_BONUS_MEDIA_BYTES = 10 * 1024 * 1024
BONUS_TYPES = {"welcome", "birthday"}

AVATARS_DIR = Path("/app/data/avatars")
PORTFOLIO_DIR = Path("/app/data/portfolio")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Allowed image formats with their magic byte signatures.
# SVG is intentionally excluded — it supports inline <script> tags.
_IMAGE_MAGIC: list[tuple[bytes, str, str]] = [
    (b"\xff\xd8\xff", ".jpg", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", ".png", "image/png"),
    (b"GIF87a", ".gif", "image/gif"),
    (b"GIF89a", ".gif", "image/gif"),
    (b"RIFF", ".webp", "image/webp"),  # full check: bytes[8:12] == b"WEBP"
]


def _detect_image(data: bytes) -> tuple[str, str] | None:
    """Return (extension, mime_type) by inspecting magic bytes, or None if unrecognised."""
    for magic, ext, mime in _IMAGE_MAGIC:
        if data[:len(magic)] == magic:
            # Extra check for WebP: RIFF????WEBP
            if magic == b"RIFF" and data[8:12] != b"WEBP":
                continue
            return ext, mime
    return None


def _bonus_photo_field(bonus_type: str) -> str:
    if bonus_type == "welcome":
        return "welcome_photo_id"
    if bonus_type == "birthday":
        return "birthday_photo_id"
    raise HTTPException(status_code=400, detail="bonus_type must be one of: welcome, birthday")


async def _media_url_from_ref(media_ref: Optional[str], request: Request) -> Optional[str]:
    if not media_ref:
        return None
    if media_ref.startswith("local:"):
        raw_path = media_ref[len("local:"):]
        path = Path(raw_path).resolve()
        try:
            path.relative_to(BONUS_MEDIA_DIR.resolve())
        except Exception:
            return None
        return f"/bonus-media/{path.name}"
    if media_ref.startswith("http://") or media_ref.startswith("https://"):
        return media_ref
    # Telegram file_id — proxy through our own endpoint to avoid leaking bot token
    if _master_bot:
        return f"/api/master/media/{media_ref}"
    return None


def _cleanup_local_media(media_ref: Optional[str]) -> None:
    if not media_ref or not media_ref.startswith("local:"):
        return
    raw_path = media_ref[len("local:"):]
    path = Path(raw_path).resolve()
    try:
        path.relative_to(BONUS_MEDIA_DIR.resolve())
    except Exception:
        return
    if path.exists() and path.is_file():
        try:
            path.unlink()
        except Exception:
            logger.warning("Failed to remove stale bonus media: %s", path)


# =============================================================================
# Profile
# =============================================================================

def _extract_username(raw: str, hosts: set[str]) -> Optional[str]:
    value = (raw or "").strip()
    if not value:
        return None
    if value.startswith("@"):
        return value[1:].strip()
    if "://" in value or "/" in value:
        parsed = urlparse(value if "://" in value else f"https://{value}")
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host not in hosts:
            return None
        first_part = (parsed.path or "").strip("/").split("/", 1)[0]
        if first_part.startswith("@"):
            first_part = first_part[1:]
        return first_part.strip() or None
    return value


def _normalize_website(raw: str) -> Optional[str]:
    value = (raw or "").strip()
    if not value:
        return None
    candidate = value if "://" in value else f"https://{value}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return candidate


def _compose_legacy_socials(telegram: Optional[str], instagram: Optional[str], website: Optional[str]) -> Optional[str]:
    parts = [p for p in [telegram, instagram, website] if p]
    return " · ".join(parts) if parts else None

class ProfileUpdateBody(BaseModel):
    name: Optional[str] = None
    sphere: Optional[str] = None
    contacts: Optional[str] = None
    socials: Optional[str] = None
    work_hours: Optional[str] = None
    phone: Optional[str] = None
    telegram: Optional[str] = None
    instagram: Optional[str] = None
    website: Optional[str] = None
    contact_address: Optional[str] = None
    about: Optional[str] = None
    avatar_file_id: Optional[str] = None
    work_mode: Optional[str] = None
    work_address_default: Optional[str] = None
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

    @field_validator("work_mode")
    @classmethod
    def work_mode_allowed(cls, v):
        if v is None:
            return v
        if v not in {"home", "travel"}:
            raise ValueError("work_mode must be one of: home, travel")
        return v

    @field_validator("phone")
    @classmethod
    def phone_normalized(cls, v):
        if v is None:
            return v
        value = v.strip()
        if not value:
            return ""
        normalized = normalize_phone(value)
        if normalized:
            return normalized
        digits = re.sub(r"\D", "", value)
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError("invalid phone number")
        return f"+{digits}" if not value.startswith("+") else f"+{digits}"

    @field_validator("telegram")
    @classmethod
    def telegram_valid(cls, v):
        if v is None:
            return v
        value = v.strip()
        if not value:
            return ""
        username = _extract_username(value, {"t.me", "telegram.me"})
        if not username or not TELEGRAM_USERNAME_RE.fullmatch(username):
            raise ValueError("invalid telegram username or link")
        return f"@{username}"

    @field_validator("instagram")
    @classmethod
    def instagram_valid(cls, v):
        if v is None:
            return v
        value = v.strip()
        if not value:
            return ""
        username = _extract_username(value, {"instagram.com", "instagr.am"})
        if not username or not INSTAGRAM_USERNAME_RE.fullmatch(username):
            raise ValueError("invalid instagram username or link")
        return f"@{username}"

    @field_validator("website")
    @classmethod
    def website_valid(cls, v):
        if v is None:
            return v
        value = v.strip()
        if not value:
            return ""
        normalized = _normalize_website(value)
        if not normalized:
            raise ValueError("invalid website url")
        return normalized

    @field_validator("contact_address")
    @classmethod
    def contact_address_len(cls, v):
        if v is None:
            return v
        value = v.strip()
        if not value:
            return ""
        if len(value) > 400:
            raise ValueError("contact_address max 400 chars")
        return value

    @field_validator("about")
    @classmethod
    def about_len(cls, v):
        if v is None:
            return v
        value = v.strip()
        if not value:
            return ""
        if len(value) > 1000:
            raise ValueError("about max 1000 chars")
        return value


@router.put("/master/profile")
async def update_master_profile(
    body: ProfileUpdateBody,
    master: Master = Depends(get_current_master),
):
    """Update master profile fields."""
    payload = body.model_dump(exclude_unset=True)
    kwargs = dict(payload)
    nullable_text_fields = {
        "sphere", "contacts", "socials", "work_hours", "phone",
        "telegram", "instagram", "website", "contact_address",
        "work_address_default", "about", "avatar_file_id",
    }
    for key in nullable_text_fields:
        if key in kwargs and isinstance(kwargs[key], str):
            kwargs[key] = kwargs[key].strip() or None
    structured_fields = {"phone", "telegram", "instagram", "website", "contact_address"}
    structured_touched = any(field in payload for field in structured_fields)

    if structured_touched:
        next_phone = kwargs["phone"] if "phone" in kwargs else master.phone
        next_telegram = kwargs["telegram"] if "telegram" in kwargs else master.telegram
        next_instagram = kwargs["instagram"] if "instagram" in kwargs else master.instagram
        next_website = kwargs["website"] if "website" in kwargs else master.website

        # Keep legacy fields in sync for older bot/UI readers.
        if "contacts" not in payload:
            kwargs["contacts"] = next_phone
        if "socials" not in payload:
            kwargs["socials"] = _compose_legacy_socials(next_telegram, next_instagram, next_website)

    if kwargs:
        await update_master(master.id, **kwargs)
    return {"ok": True}


# =============================================================================
# Google Calendar (Mini App)
# =============================================================================

@router.get("/master/google-calendar")
async def get_master_google_calendar(
    master: Master = Depends(get_current_master),
):
    """Get Google Calendar connection status for current master."""
    email = await google_calendar.get_calendar_account(master.id)
    return {
        "connected": bool(email),
        "email": email,
    }


@router.post("/master/google-calendar/connect")
async def get_master_google_calendar_connect_url(
    master: Master = Depends(get_current_master),
):
    """Generate fresh OAuth URL for Google Calendar connection."""
    url = await google_calendar.get_oauth_url(master.id)
    return {"url": url}


@router.post("/master/google-calendar/disconnect")
async def disconnect_master_google_calendar(
    master: Master = Depends(get_current_master),
):
    """Disconnect Google Calendar for current master."""
    await google_calendar.disconnect_calendar(master.id)
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
    request: Request,
    master: Master = Depends(get_current_master),
):
    welcome_photo_url = await _media_url_from_ref(master.welcome_photo_id, request)
    birthday_photo_url = await _media_url_from_ref(master.birthday_photo_id, request)
    return {
        "bonus_enabled": master.bonus_enabled,
        "bonus_rate": master.bonus_rate,
        "bonus_max_spend": master.bonus_max_spend,
        "bonus_birthday": master.bonus_birthday,
        "bonus_welcome": master.bonus_welcome,
        "welcome_message": master.welcome_message,
        "birthday_message": master.birthday_message,
        "welcome_photo_url": welcome_photo_url,
        "birthday_photo_url": birthday_photo_url,
    }


class BonusSettingsBody(BaseModel):
    bonus_enabled: Optional[bool] = None
    bonus_rate: Optional[float] = None
    bonus_max_spend: Optional[float] = None
    bonus_birthday: Optional[int] = None
    bonus_welcome: Optional[int] = None
    welcome_message: Optional[str] = None
    birthday_message: Optional[str] = None

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
    kwargs = body.model_dump(exclude_unset=True)
    if "welcome_message" in kwargs and kwargs["welcome_message"] is not None:
        stripped = kwargs["welcome_message"].strip()
        kwargs["welcome_message"] = stripped or None
    if "birthday_message" in kwargs and kwargs["birthday_message"] is not None:
        stripped = kwargs["birthday_message"].strip()
        kwargs["birthday_message"] = stripped or None
    if kwargs:
        await update_master(master.id, **kwargs)
    return {"ok": True}


class FeedbackSettingsBody(BaseModel):
    feedback_delay_hours: int = 3
    feedback_message: Optional[str] = None
    feedback_reply_5: Optional[str] = None
    review_buttons: Optional[list[dict]] = None

    @field_validator("feedback_delay_hours")
    @classmethod
    def delay_in_range(cls, v):
        if not (1 <= v <= 72):
            raise ValueError("feedback_delay_hours must be between 1 and 72")
        return v

    @field_validator("review_buttons")
    @classmethod
    def review_buttons_valid(cls, v):
        if v is None:
            return v
        if len(v) > 3:
            raise ValueError("review_buttons: max 3 allowed")
        for btn in v:
            if not isinstance(btn, dict):
                raise ValueError("review_buttons: each item must be an object")
            label = str(btn.get("label", "")).strip()
            url = str(btn.get("url", "")).strip()
            if not label:
                raise ValueError("review_buttons: label is required")
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError(f"review_buttons: invalid URL '{url}'")
        return v


@router.put("/master/settings/feedback")
async def update_feedback_settings(
    body: FeedbackSettingsBody,
    master: Master = Depends(get_current_master),
):
    """Save master post-order feedback settings."""
    review_buttons_json = (
        json.dumps(body.review_buttons, ensure_ascii=False)
        if body.review_buttons is not None
        else None
    )
    await update_master(
        master.id,
        feedback_delay_hours=body.feedback_delay_hours,
        feedback_message=(body.feedback_message or "").strip() or None,
        feedback_reply_5=(body.feedback_reply_5 or "").strip() or None,
        review_buttons=review_buttons_json,
    )
    return {"success": True}


@router.get("/master/settings/feedback")
async def get_feedback_settings(
    master: Master = Depends(get_current_master),
):
    """Get master post-order feedback settings."""
    current_master = await get_master_by_id(master.id)
    if not current_master:
        raise HTTPException(status_code=404, detail="Master not found")

    review_buttons = []
    if current_master.review_buttons:
        try:
            parsed = json.loads(current_master.review_buttons)
            if isinstance(parsed, list):
                review_buttons = parsed
        except Exception:
            review_buttons = []

    return {
        "feedback_delay_hours": current_master.feedback_delay_hours or 3,
        "feedback_message": current_master.feedback_message,
        "feedback_reply_5": current_master.feedback_reply_5,
        "review_buttons": review_buttons,
    }


@router.post("/master/bonus-settings/{bonus_type}/photo")
async def upload_bonus_photo(
    bonus_type: str,
    request: Request,
    photo: UploadFile = File(...),
    master: Master = Depends(get_current_master),
):
    """Upload greeting/birthday image from miniapp."""
    if bonus_type not in BONUS_TYPES:
        raise HTTPException(status_code=400, detail="bonus_type must be one of: welcome, birthday")

    media_bytes = await photo.read()
    if not media_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(media_bytes) > MAX_BONUS_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 10 MB limit")

    # Verify file format by magic bytes — Content-Type header is attacker-controlled
    # and would allow SVG (image/svg+xml supports inline <script>).
    detected = _detect_image(media_bytes)
    if detected is None:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file format. Allowed: JPEG, PNG, GIF, WebP.",
        )
    ext, _mime = detected

    BONUS_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"m{master.id}_{bonus_type}_{secrets.token_hex(12)}{ext}"
    file_path = (BONUS_MEDIA_DIR / filename).resolve()
    file_path.write_bytes(media_bytes)

    current_master = await get_master_by_id(master.id)
    field = _bonus_photo_field(bonus_type)
    old_ref = getattr(current_master, field) if current_master else None
    new_ref = f"local:{file_path}"

    await update_master(master.id, **{field: new_ref})
    _cleanup_local_media(old_ref)

    return {"ok": True, "photo_url": await _media_url_from_ref(new_ref, request)}


@router.delete("/master/bonus-settings/{bonus_type}/photo")
async def delete_bonus_photo(
    bonus_type: str,
    master: Master = Depends(get_current_master),
):
    """Delete greeting/birthday image reference."""
    if bonus_type not in BONUS_TYPES:
        raise HTTPException(status_code=400, detail="bonus_type must be one of: welcome, birthday")

    current_master = await get_master_by_id(master.id)
    field = _bonus_photo_field(bonus_type)
    old_ref = getattr(current_master, field) if current_master else None

    await update_master(master.id, **{field: None})
    _cleanup_local_media(old_ref)
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
            "show_on_landing": s.show_on_landing,
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
    show_on_landing: Optional[bool] = None

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


class PortfolioPhotoBody(BaseModel):
    file_id: str

    @field_validator("file_id")
    @classmethod
    def file_id_not_empty(cls, v):
        value = v.strip()
        if not value:
            raise ValueError("file_id required")
        if "/" in value or value.startswith(("http://", "https://")):
            raise ValueError("invalid file_id")
        return value


def _portfolio_item_response(item: dict) -> dict:
    file_id = item["file_id"]
    url = file_id if file_id.startswith("/") else f"/api/public/photo/{file_id}"
    return {
        "id": item["id"],
        "file_id": file_id,
        "sort_order": item.get("sort_order") or 0,
        "url": url,
    }


@router.get("/master/portfolio")
async def get_master_portfolio_api(
    master: Master = Depends(get_current_master),
):
    photos = await get_master_portfolio(master.id)
    return [_portfolio_item_response(item) for item in photos]


@router.post("/master/portfolio", status_code=201)
async def add_master_portfolio_photo(
    body: PortfolioPhotoBody,
    master: Master = Depends(get_current_master),
):
    photo_id = await add_portfolio_photo(master.id, body.file_id)
    if photo_id is None:
        raise HTTPException(status_code=409, detail="Portfolio photo limit reached")
    return {
        "id": photo_id,
        "file_id": body.file_id,
        "url": f"/api/public/photo/{body.file_id}",
    }


@router.delete("/master/portfolio/{photo_id}")
async def delete_master_portfolio_photo(
    photo_id: int,
    master: Master = Depends(get_current_master),
):
    # Fetch before delete to get file path for disk cleanup
    photos = await get_master_portfolio(master.id)
    photo = next((p for p in photos if p["id"] == photo_id), None)

    ok = await delete_portfolio_photo(photo_id, master.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Portfolio photo not found")

    if photo and photo.get("file_id", "").startswith("/portfolio/"):
        filename = photo["file_id"][len("/portfolio/"):]
        path = (PORTFOLIO_DIR / filename).resolve()
        try:
            path.relative_to(PORTFOLIO_DIR.resolve())
            if path.is_file():
                path.unlink()
        except Exception:
            logger.warning("Failed to remove portfolio photo: %s", path)

    return {"ok": True}


# =============================================================================
# Avatar and portfolio upload (multipart)
# =============================================================================

@router.post("/master/avatar/upload")
async def upload_master_avatar(
    file: UploadFile = File(...),
    master: Master = Depends(get_current_master),
):
    """Upload master avatar from Mini App (multipart)."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 10 MB limit")
    detected = _detect_image(data)
    if detected is None:
        raise HTTPException(status_code=415, detail="Unsupported format. Allowed: JPEG, PNG, GIF, WebP.")
    ext, _ = detected
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"master_{master.id}{ext}"
    (AVATARS_DIR / filename).write_bytes(data)
    avatar_url = f"/avatars/{filename}"
    await update_master(master.id, avatar_file_id=avatar_url)
    return {"avatar_url": avatar_url}


@router.delete("/master/avatar")
async def delete_master_avatar(
    master: Master = Depends(get_current_master),
):
    """Delete master avatar."""
    current = await get_master_by_id(master.id)
    if current and current.avatar_file_id and current.avatar_file_id.startswith("/avatars/"):
        filename = current.avatar_file_id[len("/avatars/"):]
        path = (AVATARS_DIR / filename).resolve()
        try:
            path.relative_to(AVATARS_DIR.resolve())
            if path.is_file():
                path.unlink()
        except Exception:
            logger.warning("Failed to remove avatar: %s", path)
    await update_master(master.id, avatar_file_id=None)
    return {"ok": True}


@router.post("/master/portfolio/upload", status_code=201)
async def upload_master_portfolio_photo(
    file: UploadFile = File(...),
    master: Master = Depends(get_current_master),
):
    """Upload portfolio photo from Mini App (multipart)."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 10 MB limit")
    detected = _detect_image(data)
    if detected is None:
        raise HTTPException(status_code=415, detail="Unsupported format. Allowed: JPEG, PNG, GIF, WebP.")
    ext, _ = detected
    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"master_{master.id}_{secrets.token_hex(8)}{ext}"
    file_path = PORTFOLIO_DIR / filename
    file_path.write_bytes(data)
    photo_url = f"/portfolio/{filename}"
    photo_id = await add_portfolio_photo(master.id, photo_url)
    if photo_id is None:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="Portfolio photo limit reached")
    return {"id": photo_id, "url": photo_url}


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


# =============================================================================
# Telegram media proxy — serves Telegram files without exposing bot token
# =============================================================================

@router.get("/master/media/{file_id:path}")
async def proxy_telegram_media(file_id: str):
    """
    Proxy a Telegram file by file_id without leaking the bot token.

    The bot token is used server-side only; the client receives the raw bytes.
    """
    if not _master_bot:
        raise HTTPException(status_code=503, detail="Bot not available")

    # Reject anything that looks like a path traversal or URL
    if "/" in file_id or file_id.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid file_id")

    try:
        file_info = await _master_bot.get_file(file_id)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_bytes = await _master_bot.download_file(file_info.file_path)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to download file")

    # Detect media type from file extension
    ext = (file_info.file_path or "").rsplit(".", 1)[-1].lower()
    media_type_map = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
        "gif": "image/gif", "mp4": "video/mp4",
    }
    content_type = media_type_map.get(ext, "application/octet-stream")

    return StreamingResponse(file_bytes, media_type=content_type)
