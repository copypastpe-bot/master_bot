"""Public landing endpoints without Telegram initData authorization."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.config import CLIENT_BOT_USERNAME
from src.database import get_landing_data

router = APIRouter(tags=["public"])
_master_bot = None


def set_master_bot(bot) -> None:
    """Store bot instance for server-side Telegram media downloads."""
    global _master_bot
    _master_bot = bot


def _photo_url(file_id: str | None) -> str | None:
    if not file_id:
        return None
    if file_id.startswith("/"):
        return file_id
    return f"/api/public/photo/{file_id}"


def _cta_link(invite_token: str) -> str:
    return f"https://t.me/{CLIENT_BOT_USERNAME}?start={invite_token}"


@router.get("/public/master/{invite_token}")
async def get_public_master(invite_token: str):
    """Return public landing read model for a master invite token."""
    data = await get_landing_data(invite_token)
    if not data:
        raise HTTPException(status_code=404, detail="Master not found")

    avatar_file_id = data.get("avatar_file_id")
    portfolio = [
        {
            "id": item["id"],
            "url": _photo_url(item.get("file_id")),
        }
        for item in data.get("portfolio", [])
    ]

    return {
        "name": data.get("name"),
        "sphere": data.get("sphere"),
        "about": data.get("about"),
        "contacts": data.get("contacts"),
        "socials": data.get("socials"),
        "work_hours": data.get("work_hours"),
        "currency": data.get("currency"),
        "bonus_enabled": data.get("bonus_enabled"),
        "bonus_welcome": data.get("bonus_welcome"),
        "avatar_url": _photo_url(avatar_file_id),
        "portfolio": portfolio,
        "services": data.get("services", []),
        "reviews": data.get("reviews", []),
        "cta_link": _cta_link(data.get("invite_token") or invite_token),
    }


@router.get("/public/photo/{file_id:path}")
async def proxy_public_photo(file_id: str):
    """Proxy a Telegram image by file_id for browser-safe public landing rendering."""
    if not _master_bot:
        raise HTTPException(status_code=503, detail="Bot not available")
    if "/" in file_id or file_id.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid file_id")

    try:
        file_info = await _master_bot.get_file(file_id)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_bytes = await _master_bot.download_file(file_info.file_path)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to download file")

    ext = (file_info.file_path or "").rsplit(".", 1)[-1].lower()
    content_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
    }.get(ext, "image/jpeg")

    return StreamingResponse(
        file_bytes,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
