"""Promo page constructor endpoints."""

import os
import re
from io import BytesIO
from pathlib import Path
from typing import Optional

import qrcode
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field, field_validator

from src.api.dependencies import get_current_master
from src.config import CLIENT_BOT_USERNAME
from src.database import (
    create_promo_page,
    ensure_unique_promo_slug,
    get_promo_categories,
    get_promo_page_by_master,
    get_promo_public_data,
    get_promo_slug_suggestions,
    increment_promo_page_clicks,
    promo_slug_exists,
    promo_style_belongs_to_category,
    set_promo_page_published,
    update_promo_page,
    update_promo_page_media,
    validate_promo_slug,
)
from src.models import Master

router = APIRouter(tags=["promo-pages"])


def _resolve_promo_media_dir() -> Path:
    path = Path(os.getenv("PROMO_MEDIA_DIR", "/app/data/promo"))
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except PermissionError:
        fallback = Path("/tmp/master_bot_promo_media")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


PROMO_MEDIA_DIR = _resolve_promo_media_dir()
PROMO_PUBLIC_BASE_URL = os.getenv("PROMO_PUBLIC_BASE_URL", "https://api.crmfit.ru")
MAX_PROMO_PHOTO_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


class PromoAdvantageBody(BaseModel):
    text: str = Field(min_length=2, max_length=60)
    icon: Optional[str] = Field(default=None, max_length=16)

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("advantage text is required")
        return value


class PromoPageBody(BaseModel):
    category_id: int
    style_id: int
    display_name: str = Field(min_length=2, max_length=60)
    specialization: str = Field(min_length=2, max_length=80)
    tagline: str = Field(min_length=10, max_length=120)
    badge_text: Optional[str] = Field(default=None, max_length=40)
    service_name: str = Field(min_length=2, max_length=100)
    service_price: str = Field(min_length=1, max_length=30)
    promo_text: Optional[str] = Field(default=None, max_length=60)
    promo_enabled: bool = False
    advantages: list[PromoAdvantageBody]
    sub_button_text: str = Field(default="Бонусы и уведомления в Telegram", max_length=60)

    @field_validator(
        "display_name",
        "specialization",
        "tagline",
        "badge_text",
        "service_name",
        "service_price",
        "promo_text",
        "sub_button_text",
    )
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("advantages")
    @classmethod
    def exactly_three_advantages(cls, value: list[PromoAdvantageBody]) -> list[PromoAdvantageBody]:
        if len(value) != 3:
            raise ValueError("Exactly 3 advantages are required")
        return value

    def db_payload(self) -> dict:
        data = self.model_dump()
        data["advantages"] = [item.model_dump() for item in self.advantages]
        return data


class SlugBody(BaseModel):
    slug: str

    @field_validator("slug")
    @classmethod
    def validate_slug_body(cls, value: str) -> str:
        return validate_promo_slug(value)


def _page_url(slug: str) -> str:
    return f"{PROMO_PUBLIC_BASE_URL.rstrip('/')}/m/{slug}"


def _media_url(master_id: int, filename: str) -> str:
    return f"/media/promo/{master_id}/{filename}"


def _bot_link(master_id: int) -> str:
    return f"https://t.me/{CLIENT_BOT_USERNAME}?start=promo_{master_id}"


def _page_response(page: dict) -> dict:
    return {
        **page,
        "page_url": _page_url(page["slug"]),
        "bot_link": _bot_link(page["master_id"]),
    }


def _public_response(data: dict) -> dict:
    style = data.get("style", {}).get("config", {})
    return {
        "display_name": data["display_name"],
        "specialization": data["specialization"],
        "tagline": data["tagline"],
        "badge_text": data.get("badge_text"),
        "service_name": data["service_name"],
        "service_price": data["service_price"],
        "promo_text": data.get("promo_text"),
        "promo_enabled": data.get("promo_enabled", False),
        "advantages": data.get("advantages", []),
        "sub_button_text": data.get("sub_button_text"),
        "photo_url": data.get("photo_url"),
        "style": style,
        "category": data.get("category"),
        "bot_link": _bot_link(data["master_id"]),
        "master_name": data.get("master_name"),
        "slug": data["slug"],
        "page_url": _page_url(data["slug"]),
    }


async def _validate_category_style(category_id: int, style_id: int) -> None:
    if not await promo_style_belongs_to_category(style_id, category_id):
        raise HTTPException(status_code=400, detail="Style does not belong to category")


async def _sync_qr(page: dict) -> dict:
    master_id = page["master_id"]
    page_url = _page_url(page["slug"])
    master_dir = PROMO_MEDIA_DIR / str(master_id)
    master_dir.mkdir(parents=True, exist_ok=True)

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(page_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    image = image.resize((512, 512), Image.Resampling.NEAREST)

    qr_path = master_dir / "qr.png"
    image.save(qr_path, format="PNG")
    updated = await update_promo_page_media(
        master_id,
        qr_path=str(qr_path),
        qr_url=_media_url(master_id, "qr.png"),
    )
    return updated or page


async def _read_image(file: UploadFile) -> tuple[bytes, Image.Image, str]:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_PROMO_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 5 MB limit")

    try:
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=415, detail="Unsupported format. Allowed: JPEG, PNG, WebP.")

    image_format = (image.format or "").upper()
    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(status_code=415, detail="Unsupported format. Allowed: JPEG, PNG, WebP.")
    if image.width < 200 or image.height < 200:
        raise HTTPException(status_code=400, detail="Image must be at least 200x200 px")
    return data, image, ALLOWED_IMAGE_FORMATS[image_format]


def _save_optimized_photo(master_id: int, data: bytes, image: Image.Image, original_ext: str) -> tuple[str, str]:
    master_dir = PROMO_MEDIA_DIR / str(master_id)
    master_dir.mkdir(parents=True, exist_ok=True)

    original_path = master_dir / f"photo_original{original_ext}"
    original_path.write_bytes(data)

    normalized = ImageOps.exif_transpose(image)
    if normalized.mode in {"RGBA", "LA"}:
        background = Image.new("RGB", normalized.size, (255, 255, 255))
        background.paste(normalized, mask=normalized.getchannel("A"))
        normalized = background
    elif normalized.mode != "RGB":
        normalized = normalized.convert("RGB")

    normalized.thumbnail((800, 800), Image.Resampling.LANCZOS)
    photo_path = master_dir / "photo.jpg"
    normalized.save(photo_path, format="JPEG", quality=85, optimize=True)
    return str(photo_path), _media_url(master_id, "photo.jpg")


@router.get("/promo/categories")
async def get_promo_categories_api(_master: Master = Depends(get_current_master)):
    """Return active promo categories with styles and advantage presets."""
    return {"categories": await get_promo_categories()}


@router.get("/promo/page")
async def get_promo_page_api(master: Master = Depends(get_current_master)):
    page = await get_promo_page_by_master(master.id)
    if not page:
        raise HTTPException(status_code=404, detail="Promo page not found")
    return _page_response(page)


@router.post("/promo/page", status_code=201)
async def create_promo_page_api(
    body: PromoPageBody,
    master: Master = Depends(get_current_master),
):
    await _validate_category_style(body.category_id, body.style_id)
    existing = await get_promo_page_by_master(master.id)
    if existing:
        raise HTTPException(status_code=409, detail="Promo page already exists")

    page = await create_promo_page(master.id, **body.db_payload())
    page = await _sync_qr(page)
    return _page_response(page)


@router.put("/promo/page")
async def update_promo_page_api(
    body: PromoPageBody,
    master: Master = Depends(get_current_master),
):
    await _validate_category_style(body.category_id, body.style_id)
    existing = await get_promo_page_by_master(master.id)
    if not existing:
        raise HTTPException(status_code=404, detail="Promo page not found")

    page = await update_promo_page(master.id, **body.db_payload())
    if not page:
        raise HTTPException(status_code=404, detail="Promo page not found")
    return _page_response(page)


@router.post("/promo/page/publish")
async def publish_promo_page_api(master: Master = Depends(get_current_master)):
    page = await get_promo_page_by_master(master.id)
    if not page:
        raise HTTPException(status_code=404, detail="Promo page not found")
    if not page.get("photo_url"):
        raise HTTPException(status_code=400, detail="Upload photo before publishing")

    page = await set_promo_page_published(master.id, True)
    if not page:
        raise HTTPException(status_code=404, detail="Promo page not found")
    return _page_response(page)


@router.post("/promo/page/unpublish")
async def unpublish_promo_page_api(master: Master = Depends(get_current_master)):
    page = await set_promo_page_published(master.id, False)
    if not page:
        raise HTTPException(status_code=404, detail="Promo page not found")
    return _page_response(page)


@router.post("/promo/photo")
async def upload_promo_photo_api(
    file: UploadFile = File(...),
    master: Master = Depends(get_current_master),
):
    page = await get_promo_page_by_master(master.id)
    if not page:
        raise HTTPException(status_code=404, detail="Create promo page before uploading photo")

    data, image, original_ext = await _read_image(file)
    photo_path, photo_url = _save_optimized_photo(master.id, data, image, original_ext)
    page = await update_promo_page_media(master.id, photo_path=photo_path, photo_url=photo_url)
    if not page:
        raise HTTPException(status_code=404, detail="Promo page not found")
    return {"photo_url": photo_url, "page": _page_response(page)}


@router.get("/promo/slug/check")
async def check_promo_slug_api(
    slug: str = Query(..., min_length=1),
    master: Master = Depends(get_current_master),
):
    try:
        normalized = validate_promo_slug(slug)
    except ValueError:
        generated = await ensure_unique_promo_slug(slug, exclude_master_id=master.id)
        return {"available": False, "suggestions": [generated]}

    available = not await promo_slug_exists(normalized, exclude_master_id=master.id)
    if available:
        return {"available": True}
    suggestions = await get_promo_slug_suggestions(normalized, exclude_master_id=master.id)
    return {"available": False, "suggestions": suggestions}


@router.put("/promo/page/slug")
async def update_promo_slug_api(
    body: SlugBody,
    master: Master = Depends(get_current_master),
):
    existing = await get_promo_page_by_master(master.id)
    if not existing:
        raise HTTPException(status_code=404, detail="Promo page not found")
    if await promo_slug_exists(body.slug, exclude_master_id=master.id):
        raise HTTPException(status_code=409, detail="Slug is already taken")

    page = await update_promo_page(master.id, slug=body.slug)
    if not page:
        raise HTTPException(status_code=404, detail="Promo page not found")
    page = await _sync_qr(page)
    return _page_response(page)


@router.get("/promo/public/{slug}")
async def get_public_promo_page_api(slug: str):
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,48}[a-z0-9])", slug):
        raise HTTPException(status_code=404, detail="Promo page not found")
    data = await get_promo_public_data(slug, increment_view=True)
    if not data:
        raise HTTPException(status_code=404, detail="Promo page not found")
    return _public_response(data)


@router.post("/promo/public/{slug}/click")
async def track_public_promo_click_api(slug: str):
    ok = await increment_promo_page_clicks(slug)
    if not ok:
        raise HTTPException(status_code=404, detail="Promo page not found")
    return {"ok": True}
