"""Orders endpoints - history and order requests."""

from fastapi import APIRouter, Depends, Form, UploadFile, File
from typing import Optional

from src.api.dependencies import get_current_client
from src.database import get_client_orders, save_inbound_request, update_inbound_request_notification_id
from src.keyboards import request_notify_kb
from src.models import Client, Master, MasterClient
from aiogram.types import BufferedInputFile

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
    media: Optional[UploadFile] = File(None),
    media_type: Optional[str] = Form(None),
    data: tuple[Client, Master, MasterClient] = Depends(get_current_client)
):
    """Create an order request (inbound request to master)."""
    client, master, master_client = data

    file_id = None

    # Send media to master via master_bot and get file_id
    if media and media_type and _master_bot:
        media_bytes = await media.read()
        caption = f"📎 Файл к заявке от {client.name}"
        try:
            if media_type == "photo":
                msg = await _master_bot.send_photo(
                    master.tg_id,
                    photo=BufferedInputFile(media_bytes, filename=media.filename or "photo.jpg"),
                    caption=caption,
                )
                file_id = msg.photo[-1].file_id
            elif media_type == "video":
                msg = await _master_bot.send_video(
                    master.tg_id,
                    video=BufferedInputFile(media_bytes, filename=media.filename or "video.mp4"),
                    caption=caption,
                )
                file_id = msg.video.file_id
        except Exception:
            pass  # не блокируем заявку если медиа не отправилось

    request_id = await save_inbound_request(
        master_id=master.id,
        client_id=client.id,
        type="order_request",
        text=comment,
        service_name=service_name,
        file_id=file_id,
        desired_date=desired_date,
        desired_time=desired_time,
        media_type=media_type,
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
                reply_markup=request_notify_kb(request_id)
            )
            await update_inbound_request_notification_id(request_id, sent.message_id)
        except Exception:
            pass

    return {"success": True}
