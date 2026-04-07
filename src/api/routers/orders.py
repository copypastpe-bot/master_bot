"""Orders endpoints - history and order requests."""

import logging
from fastapi import APIRouter, Depends, Form, UploadFile, File
from typing import Optional

from src.api.dependencies import get_current_client
from src.database import (
    get_client_orders,
    save_inbound_request,
    save_inbound_request_media,
    update_inbound_request_notification_id,
)
from src.keyboards import request_notify_kb
from src.models import Client, Master, MasterClient
from aiogram.types import BufferedInputFile

logger = logging.getLogger(__name__)

router = APIRouter(tags=["orders"])

# Master bot instance for sending notifications
_master_bot = None


def set_master_bot(bot):
    """Set master bot instance for notifications."""
    global _master_bot
    _master_bot = bot


@router.get("/orders")
async def get_orders(
    data: tuple[Client, Master, MasterClient] = Depends(get_current_client)
):
    """Get client's order history (last 20 orders)."""
    client, master, master_client = data

    orders = await get_client_orders(master.id, client.id, limit=20)

    return [
        {
            "id": order["id"],
            "scheduled_at": order["scheduled_at"],
            "status": order["status"],
            "services": order.get("services", ""),
            "amount_total": order["amount_total"],
            "bonus_accrued": order["bonus_accrued"],
            "address": order["address"],
        }
        for order in orders
    ]


@router.post("/orders/request")
async def create_order_request(
    service_name: str = Form(...),
    comment: Optional[str] = Form(None),
    desired_date: Optional[str] = Form(None),
    desired_time: Optional[str] = Form(None),
    media: Optional[list[UploadFile]] = File(None),
    media_type: Optional[str] = Form(None),
    data: tuple[Client, Master, MasterClient] = Depends(get_current_client)
):
    """Create an order request (inbound request to master)."""
    client, master, master_client = data

    file_id = None
    stored_media_type = None
    media_files = media or []
    sent_media: list[dict] = []

    # Send all attached files to master. Keep first file_id for miniapp preview.
    if media_files and _master_bot:
        caption = f"📎 Файл к заявке от {client.name}"
        for item in media_files:
            try:
                content_type = (item.content_type or "").lower()
                inferred_type = "photo" if content_type.startswith("image/") else "video" if content_type.startswith("video/") else None
                current_type = inferred_type or media_type

                if current_type not in {"photo", "video"}:
                    logger.warning(
                        "Unsupported media type in order request: filename=%s content_type=%s media_type=%s",
                        item.filename, item.content_type, media_type
                    )
                    continue

                media_bytes = await item.read()
                if current_type == "photo":
                    msg = await _master_bot.send_photo(
                        master.tg_id,
                        photo=BufferedInputFile(media_bytes, filename=item.filename or "photo.jpg"),
                        caption=caption,
                    )
                    current_file_id = msg.photo[-1].file_id
                else:
                    msg = await _master_bot.send_video(
                        master.tg_id,
                        video=BufferedInputFile(media_bytes, filename=item.filename or "video.mp4"),
                        caption=caption,
                    )
                    current_file_id = msg.video.file_id

                if file_id is None:
                    file_id = current_file_id
                    stored_media_type = current_type

                sent_media.append({
                    "file_id": current_file_id,
                    "media_type": current_type,
                    "notification_message_id": msg.message_id,
                    "position": len(sent_media),
                })
            except Exception as e:
                logger.warning("Failed to send media to master %s: %s", master.tg_id, e)

    request_id = await save_inbound_request(
        master_id=master.id,
        client_id=client.id,
        type="order_request",
        text=comment,
        service_name=service_name,
        file_id=file_id,
        desired_date=desired_date,
        desired_time=desired_time,
        media_type=stored_media_type,
    )
    for media_item in sent_media:
        await save_inbound_request_media(
            request_id=request_id,
            file_id=media_item["file_id"],
            media_type=media_item["media_type"],
            notification_message_id=media_item["notification_message_id"],
            position=media_item["position"],
        )

    # Text notification to master (always, even when media was sent)
    if _master_bot:
        date_line = f"\n📅 {desired_date}" if desired_date else ""
        time_line = f" в {desired_time}" if desired_time else ""
        comment_line = f"\n💬 {comment}" if comment else ""
        notify_text = (
            f"🛎 Новая заявка на запись!\n\n"
            f"👤 {client.name}\n"
            f"📞 {client.phone or '—'}\n"
            f"🛠 Услуга: {service_name}"
            f"{date_line}{time_line}{comment_line}"
        )
        try:
            sent = await _master_bot.send_message(
                master.tg_id, notify_text,
                reply_markup=request_notify_kb(request_id, client.tg_id)
            )
            await update_inbound_request_notification_id(request_id, sent.message_id)
        except Exception as e:
            logger.warning("Failed to send order request notification to master %s: %s", master.tg_id, e)

    return {"success": True}
