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
    media: Optional[list[UploadFile]] = File(None),
    media_type: Optional[str] = Form(None),
    data: tuple[Client, Master, MasterClient] = Depends(get_current_client)
):
    """Submit a question to the master."""
    client, master, master_client = data

    file_id = None
    stored_media_type = None
    media_files = media or []

    if media_files and _master_bot:
        caption = f"❓ Вопрос от {client.name}:\n{text}"
        for item in media_files:
            try:
                content_type = (item.content_type or "").lower()
                inferred_type = "photo" if content_type.startswith("image/") else "video" if content_type.startswith("video/") else None
                current_type = inferred_type or media_type

                if current_type not in {"photo", "video"}:
                    logger.warning(
                        "Unsupported media type in question: filename=%s content_type=%s media_type=%s",
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
            except Exception as e:
                logger.warning("Failed to send question media to master %s: %s", master.tg_id, e)

    request_id = await save_inbound_request(
        master_id=master.id,
        client_id=client.id,
        type="question",
        text=text,
        file_id=file_id,
        media_type=stored_media_type,
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
