"""Master requests endpoints — list, counters, detail, close."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_current_master
from src.database import (
    close_inbound_request,
    get_inbound_request_media,
    get_inbound_request_by_id,
    get_inbound_requests,
    get_inbound_requests_total,
    get_unread_requests_count,
    mark_all_requests_read,
)
from src.models import Master

router = APIRouter(tags=["master"])
logger = logging.getLogger(__name__)

_master_bot = None


def set_master_bot(bot) -> None:
    global _master_bot
    _master_bot = bot


def _normalize_status_filter(status: Optional[str]) -> Optional[str]:
    """Normalize optional status query value."""
    if status is None:
        return None

    normalized = status.strip().lower()
    if normalized in {"", "all"}:
        return None
    if normalized not in {"new", "closed"}:
        raise HTTPException(status_code=400, detail="status must be one of: new, closed, all")
    return normalized


async def _resolve_media_url(file_id: str) -> str:
    """Build Telegram file URL from Bot API file_id."""
    file_info = await _master_bot.get_file(file_id)
    from src.config import MASTER_BOT_TOKEN
    return f"https://api.telegram.org/file/bot{MASTER_BOT_TOKEN}/{file_info.file_path}"


@router.get("/master/requests")
async def list_requests(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    master: Master = Depends(get_current_master),
):
    """Get master requests with filter, pagination, total, and unread counter."""
    status_filter = _normalize_status_filter(status)
    requests = await get_inbound_requests(
        master_id=master.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    total = await get_inbound_requests_total(master.id, status=status_filter)
    unread_count = await get_unread_requests_count(master.id)
    return {
        "requests": requests,
        "total": total,
        "unread_count": unread_count,
    }


@router.get("/master/requests/unread_count")
async def unread_requests_count(
    master: Master = Depends(get_current_master),
):
    """Get unread/new requests count for current master."""
    count = await get_unread_requests_count(master.id)
    return {"count": count}


@router.get("/master/requests/{request_id}")
async def get_request(
    request_id: int,
    master: Master = Depends(get_current_master),
):
    """Get one request by id scoped to current master."""
    request_data = await get_inbound_request_by_id(request_id, master.id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Not found")
    return request_data


@router.post("/master/requests/{request_id}/close")
async def close_request(
    request_id: int,
    master: Master = Depends(get_current_master),
):
    """Close one request by id scoped to current master."""
    closed = await close_inbound_request(request_id, master.id)
    if not closed:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.get("/master/requests/{request_id}/media-url")
async def get_request_media_url(
    request_id: int,
    master: Master = Depends(get_current_master),
):
    """Return Telegram file URL for a request's attached media."""
    request_data = await get_inbound_request_by_id(request_id, master.id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Not found")
    if not _master_bot:
        raise HTTPException(status_code=404, detail="No media")

    media_items = await get_inbound_request_media(request_id, master.id)
    if not media_items:
        raise HTTPException(status_code=404, detail="No media")

    for media_item in media_items:
        file_id = media_item.get("file_id")
        if not file_id:
            continue
        try:
            return {"url": await _resolve_media_url(file_id)}
        except Exception as e:
            logger.warning(
                "Failed to resolve media URL for request_id=%s file_id=%s: %s",
                request_id, file_id, e,
            )

    raise HTTPException(status_code=404, detail="Media unavailable")


@router.get("/master/requests/{request_id}/media")
async def get_request_media(
    request_id: int,
    master: Master = Depends(get_current_master),
):
    """Return all media items for a request with resolved URLs."""
    request_data = await get_inbound_request_by_id(request_id, master.id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Not found")
    if not _master_bot:
        raise HTTPException(status_code=404, detail="No media")

    media_items = await get_inbound_request_media(request_id, master.id)
    if not media_items:
        return {"media": []}

    resolved_media: list[dict] = []
    for media_item in media_items:
        file_id = media_item.get("file_id")
        if not file_id:
            continue
        try:
            url = await _resolve_media_url(file_id)
        except Exception as e:
            logger.warning(
                "Failed to resolve media URL for request_id=%s file_id=%s: %s",
                request_id, file_id, e,
            )
            continue

        resolved_media.append({
            "id": media_item.get("id"),
            "file_id": file_id,
            "media_type": media_item.get("media_type"),
            "position": media_item.get("position"),
            "notification_message_id": media_item.get("notification_message_id"),
            "created_at": media_item.get("created_at"),
            "url": url,
        })

    return {"media": resolved_media}


@router.put("/master/requests/read-all")
async def read_all_requests(
    master: Master = Depends(get_current_master),
):
    """Backward-compatible endpoint: close all requests."""
    await mark_all_requests_read(master.id)
    return {"success": True}


@router.put("/master/requests/{request_id}/read")
async def read_request(
    request_id: int,
    master: Master = Depends(get_current_master),
):
    """Backward-compatible endpoint: close one request."""
    closed = await close_inbound_request(request_id, master.id)
    if not closed:
        raise HTTPException(status_code=404, detail="Not found")
    return {"success": True}
