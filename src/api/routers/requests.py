"""Client requests endpoints — questions to master."""

import logging
from fastapi import APIRouter, Depends, Form, UploadFile, File
from typing import Optional

from src.api.dependencies import get_current_client
from src.database import save_inbound_request, update_inbound_request_notification_id
from src.keyboards import request_notify_kb
from src.models import Client, Master, MasterClient
from aiogram.types import BufferedInputFile

logger = logging.getLogger(__name__)

router = APIRouter(tags=["requests"])

_master_bot = None


def set_master_bot(bot):
    global _master_bot
    _master_bot = bot


@router.post("/requests/question")
async def create_question(
    text: str = Form(...),
    media: Optional[UploadFile] = File(None),
    media_type: Optional[str] = Form(None),
    data: tuple[Client, Master, MasterClient] = Depends(get_current_client)
):
    """Submit a question to the master."""
    client, master, master_client = data

    file_id = None

    if media and media_type and _master_bot:
        media_bytes = await media.read()
        caption = f"❓ Вопрос от {client.name}:\n{text}"
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
        except Exception as e:
            logger.warning("Failed to send question media to master %s: %s", master.tg_id, e)

    request_id = await save_inbound_request(
        master_id=master.id,
        client_id=client.id,
        type="question",
        text=text,
        file_id=file_id,
        media_type=media_type,
    )

    # Text notification with action keyboard (always sent)
    if _master_bot:
        notify_text = (
            f"❓ Вопрос от клиента\n\n"
            f"👤 {client.name}\n"
            f"📞 {client.phone or '—'}\n\n"
            f"{text}"
        )
        try:
            sent = await _master_bot.send_message(
                master.tg_id, notify_text,
                reply_markup=request_notify_kb(request_id, client.tg_id)
            )
            await update_inbound_request_notification_id(request_id, sent.message_id)
        except Exception as e:
            logger.warning("Failed to send question notification to master %s: %s", master.tg_id, e)

    return {"success": True}
