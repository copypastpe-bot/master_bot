"""Marketing handlers: broadcasts and promotions."""

import asyncio
import aiohttp
from datetime import date

from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from src.config import MASTER_BOT_TOKEN, CLIENT_BOT_TOKEN
from src.database import (
    get_master_by_tg_id,
    get_active_promos,
    get_broadcast_recipients,
    get_broadcast_recipients_count,
    save_campaign,
    get_promo_by_id,
    deactivate_promo,
)
from src.keyboards import (
    marketing_kb,
    broadcast_cancel_kb,
    broadcast_media_kb,
    broadcast_segment_kb,
    broadcast_confirm_kb,
    broadcast_no_recipients_kb,
    promo_cancel_kb,
    promo_date_from_kb,
    promo_confirm_kb,
    promo_card_kb,
    promo_end_confirm_kb,
)
from src.states import BroadcastFSM, PromoFSM
from src.handlers.common import edit_home_message
from src.utils import parse_date

import logging
logger = logging.getLogger(__name__)

router = Router(name="marketing")

SEGMENT_NAMES = {
    "all": "Все клиенты",
    "inactive_3m": "Не приходили 3+ месяца",
    "inactive_6m": "Не приходили 6+ месяцев",
    "new_30d": "Новые за 30 дней",
}


# =============================================================================
# Marketing Section
# =============================================================================

@router.callback_query(F.data == "marketing")
async def cb_marketing(callback: CallbackQuery, state: FSMContext) -> None:
    """Show marketing section with active promos."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    await state.clear()
    await state.update_data(current_screen="marketing")

    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(
            f"• {p.title}" for p in promos
        )
    else:
        promos_text = "Активных акций нет"

    text = (
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, marketing_kb(promos))
    await callback.answer()


# =============================================================================
# Broadcast FSM
# =============================================================================

@router.callback_query(F.data == "marketing:broadcast")
async def cb_marketing_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Start broadcast flow - Step 1: Text."""
    text = (
        "📨 Новая рассылка\n"
        "━━━━━━━━━━━━━━━\n"
        "Введите текст сообщения:"
    )

    await edit_home_message(callback, text, broadcast_cancel_kb())
    await state.set_state(BroadcastFSM.text)
    await callback.answer()


@router.message(BroadcastFSM.text)
async def broadcast_text(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 1: Save broadcast text."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    text_content = message.text.strip()
    await state.update_data(broadcast_text=text_content)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    text = (
        "📨 Новая рассылка\n"
        "━━━━━━━━━━━━━━━\n"
        "Прикрепить фото или видео? (необязательно)\n\n"
        "Отправьте фото/видео или нажмите «Пропустить»:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=broadcast_media_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(BroadcastFSM.media)


@router.message(BroadcastFSM.media, F.photo)
async def broadcast_media_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 2: Save photo."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    file_id = message.photo[-1].file_id  # Largest photo
    await state.update_data(broadcast_file_id=file_id, broadcast_media_type="photo")

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await show_broadcast_segment_step(bot, master, message.chat.id, state)


@router.message(BroadcastFSM.media, F.video)
async def broadcast_media_video(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 2: Save video."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    file_id = message.video.file_id
    await state.update_data(broadcast_file_id=file_id, broadcast_media_type="video")

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await show_broadcast_segment_step(bot, master, message.chat.id, state)


@router.callback_query(BroadcastFSM.media, F.data == "broadcast:media:skip")
async def broadcast_media_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 2: Skip media."""
    await state.update_data(broadcast_file_id=None, broadcast_media_type=None)

    text = (
        "📨 Новая рассылка\n"
        "━━━━━━━━━━━━━━━\n"
        "Кому отправить?"
    )

    await edit_home_message(callback, text, broadcast_segment_kb())
    await state.set_state(BroadcastFSM.segment)
    await callback.answer()


async def show_broadcast_segment_step(bot: Bot, master, chat_id: int, state: FSMContext) -> None:
    """Show segment selection step."""
    text = (
        "📨 Новая рассылка\n"
        "━━━━━━━━━━━━━━━\n"
        "📎 Медиа прикреплено\n"
        "━━━━━━━━━━━━━━━\n"
        "Кому отправить?"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=broadcast_segment_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(BroadcastFSM.segment)


@router.callback_query(BroadcastFSM.segment, F.data.startswith("broadcast:segment:"))
async def broadcast_select_segment(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Select segment and show preview."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    segment = callback.data.split(":")[2]
    await state.update_data(broadcast_segment=segment)

    # Get recipient count
    count = await get_broadcast_recipients_count(master.id, segment)

    if count == 0:
        text = (
            "📨 Рассылка\n"
            "━━━━━━━━━━━━━━━\n"
            "В этом сегменте нет клиентов с Telegram."
        )
        await edit_home_message(callback, text, broadcast_no_recipients_kb())
        await state.clear()
        await callback.answer()
        return

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    has_media = data.get("broadcast_file_id") is not None
    segment_name = SEGMENT_NAMES.get(segment, segment)

    media_text = "📎 + медиа\n" if has_media else ""

    text = (
        f"📨 Предпросмотр рассылки\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{broadcast_text}\n"
        f"{media_text}"
        f"━━━━━━━━━━━━━━━\n"
        f"Получателей: {count} клиентов\n"
        f"Сегмент: {segment_name}"
    )

    await edit_home_message(callback, text, broadcast_confirm_kb())
    await state.set_state(BroadcastFSM.confirm)
    await callback.answer()


@router.callback_query(BroadcastFSM.confirm, F.data == "broadcast:send")
async def broadcast_send(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Step 4: Send broadcast."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    file_id = data.get("broadcast_file_id")
    media_type = data.get("broadcast_media_type")
    segment = data.get("broadcast_segment", "all")

    # Show sending message
    await edit_home_message(callback, "📤 Отправка рассылки...", None)
    await callback.answer()

    # Get recipients
    recipients = await get_broadcast_recipients(master.id, segment)

    client_bot = Bot(token=CLIENT_BOT_TOKEN)

    # If there's media, download it first (file_id is bot-specific)
    media_bytes = None
    if file_id:
        try:
            file_info = await bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{MASTER_BOT_TOKEN}/{file_info.file_path}"
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    if resp.status == 200:
                        media_bytes = await resp.read()
        except Exception as e:
            logger.error(f"Broadcast: failed to download media: {e}")
            file_id = None  # Fallback to text-only

    sent = 0
    failed = 0

    for client in recipients:
        try:
            if media_bytes:
                if media_type == "photo":
                    await client_bot.send_photo(
                        chat_id=client["tg_id"],
                        photo=BufferedInputFile(media_bytes, filename="broadcast.jpg"),
                        caption=broadcast_text
                    )
                else:
                    await client_bot.send_video(
                        chat_id=client["tg_id"],
                        video=BufferedInputFile(media_bytes, filename="broadcast.mp4"),
                        caption=broadcast_text
                    )
            else:
                await client_bot.send_message(
                    chat_id=client["tg_id"],
                    text=broadcast_text
                )
            sent += 1
            await asyncio.sleep(0.05)  # 50ms pause
        except TelegramForbiddenError:
            logger.warning(f"Broadcast: client {client['tg_id']} blocked the bot")
            failed += 1
        except Exception as e:
            logger.error(f"Broadcast: failed to send to {client['tg_id']}: {e}")
            failed += 1

    await client_bot.session.close()

    # Save campaign
    await save_campaign(
        master_id=master.id,
        campaign_type="broadcast",
        title=None,
        text=broadcast_text,
        active_from=None,
        active_to=None,
        sent_count=sent,
        segment=segment
    )

    await state.clear()
    await state.update_data(current_screen="marketing")

    # Show marketing screen
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"✅ Рассылка отправлена!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Отправлено: {sent}\n"
        f"Не доставлено: {failed}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    try:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=master.home_message_id,
            text=text,
            reply_markup=marketing_kb(promos)
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "broadcast:cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel broadcast."""
    await state.clear()

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, marketing_kb(promos))
    await callback.answer("Отменено")


# =============================================================================
# Promo FSM
# =============================================================================

@router.callback_query(F.data == "marketing:promo:new")
async def cb_marketing_promo_new(callback: CallbackQuery, state: FSMContext) -> None:
    """Start promo creation - Step 1: Title."""
    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        "Введите название акции:"
    )

    await edit_home_message(callback, text, promo_cancel_kb())
    await state.set_state(PromoFSM.title)
    await callback.answer()


@router.message(PromoFSM.title)
async def promo_title(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 1: Save promo title."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    title = message.text.strip()[:100]
    await state.update_data(promo_title=title)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        "━━━━━━━━━━━━━━━\n"
        "Введите описание акции\n"
        "(условия, выгода для клиента):"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=promo_cancel_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(PromoFSM.description)


@router.message(PromoFSM.description)
async def promo_description(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 2: Save promo description."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    description = message.text.strip()[:500]
    await state.update_data(promo_description=description)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    title = data.get("promo_title")

    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Описание: {description[:50]}...\n"
        "━━━━━━━━━━━━━━━\n"
        "Дата начала акции (например: 01.03.2026)\n"
        "или нажмите «Сегодня»:"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=promo_date_from_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(PromoFSM.date_from)


@router.callback_query(PromoFSM.date_from, F.data == "promo:date_from:today")
async def promo_date_from_today(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3: Set start date to today."""
    today = date.today().isoformat()
    await state.update_data(promo_date_from=today)

    data = await state.get_data()
    title = data.get("promo_title")

    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Начало: сегодня\n"
        "━━━━━━━━━━━━━━━\n"
        "Дата окончания акции (например: 31.03.2026):"
    )

    await edit_home_message(callback, text, promo_cancel_kb())
    await state.set_state(PromoFSM.date_to)
    await callback.answer()


@router.message(PromoFSM.date_from)
async def promo_date_from_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 3: Parse start date."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        date_from_obj = parse_date(message.text.strip())
        if not date_from_obj:
            raise ValueError("Invalid date")
        date_from = date_from_obj.isoformat()
    except (ValueError, AttributeError):
        await message.answer("Неверный формат даты. Используйте ДД.ММ.ГГГГ")
        return

    await state.update_data(promo_date_from=date_from)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    title = data.get("promo_title")

    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Начало: {date_from}\n"
        "━━━━━━━━━━━━━━━\n"
        "Дата окончания акции (например: 31.03.2026):"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=promo_cancel_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(PromoFSM.date_to)


@router.message(PromoFSM.date_to)
async def promo_date_to_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 4: Parse end date and show confirmation."""
    tg_id = message.from_user.id
    master = await get_master_by_tg_id(tg_id)

    try:
        date_to_obj = parse_date(message.text.strip())
        if not date_to_obj:
            raise ValueError("Invalid date")
        date_to = date_to_obj.isoformat()
    except (ValueError, AttributeError):
        await message.answer("Неверный формат даты. Используйте ДД.ММ.ГГГГ")
        return

    data = await state.get_data()
    date_from = data.get("promo_date_from")
    today = date.today().isoformat()

    # Validate: end date must be >= today and >= start date
    if date_to < today:
        await message.answer("Дата окончания не может быть в прошлом")
        return
    if date_to < date_from:
        await message.answer("Дата окончания должна быть позже даты начала")
        return

    await state.update_data(promo_date_to=date_to)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    title = data.get("promo_title")
    description = data.get("promo_description")

    text = (
        "🎁 Новая акция\n"
        "━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Описание: {description}\n"
        f"Период: {date_from} — {date_to}\n"
        "━━━━━━━━━━━━━━━\n"
        "Разослать уведомление всем клиентам?"
    )

    if master.home_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=master.home_message_id,
                text=text,
                reply_markup=promo_confirm_kb()
            )
        except TelegramBadRequest:
            pass

    await state.set_state(PromoFSM.confirm)


@router.callback_query(PromoFSM.confirm, F.data == "promo:confirm:broadcast")
async def promo_confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Step 5: Create promo and broadcast."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    title = data.get("promo_title")
    description = data.get("promo_description")
    date_from = data.get("promo_date_from")
    date_to = data.get("promo_date_to")

    # Show sending message
    await edit_home_message(callback, "📤 Создание акции и отправка уведомлений...", None)
    await callback.answer()

    # Get recipients (all clients with notify_marketing)
    recipients = await get_broadcast_recipients(master.id, "all")

    # Send notifications via client_bot
    client_bot = Bot(token=CLIENT_BOT_TOKEN)

    sent = 0

    promo_text = (
        f"🎁 Новая акция от {master.name}!\n\n"
        f"{title}\n"
        f"{description}\n\n"
        f"📅 Действует: {date_from} — {date_to}"
    )

    for client in recipients:
        try:
            await client_bot.send_message(
                chat_id=client["tg_id"],
                text=promo_text
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await client_bot.session.close()

    # Save campaign
    await save_campaign(
        master_id=master.id,
        campaign_type="promo",
        title=title,
        text=description,
        active_from=date_from,
        active_to=date_to,
        sent_count=sent
    )

    await state.clear()
    await state.update_data(current_screen="marketing")

    # Show marketing screen
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"✅ Акция создана!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Период: {date_from} — {date_to}\n"
        f"Уведомлено клиентов: {sent}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    try:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=master.home_message_id,
            text=text,
            reply_markup=marketing_kb(promos)
        )
    except TelegramBadRequest:
        pass


@router.callback_query(PromoFSM.confirm, F.data == "promo:confirm:save")
async def promo_confirm_save(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 5: Create promo without broadcast."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    data = await state.get_data()
    title = data.get("promo_title")
    description = data.get("promo_description")
    date_from = data.get("promo_date_from")
    date_to = data.get("promo_date_to")

    # Save campaign without broadcast
    await save_campaign(
        master_id=master.id,
        campaign_type="promo",
        title=title,
        text=description,
        active_from=date_from,
        active_to=date_to,
        sent_count=0
    )

    await state.clear()
    await state.update_data(current_screen="marketing")

    # Show marketing screen
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"✅ Акция создана!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Название: {title}\n"
        f"Период: {date_from} — {date_to}\n"
        f"Уведомления не отправлялись\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, marketing_kb(promos))
    await callback.answer()


@router.callback_query(F.data == "promo:cancel")
async def promo_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel promo creation."""
    await state.clear()

    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, marketing_kb(promos))
    await callback.answer("Отменено")


# =============================================================================
# Promo Card and Management
# =============================================================================

@router.callback_query(F.data.startswith("marketing:promo:view:"))
async def cb_promo_view(callback: CallbackQuery) -> None:
    """View promo card."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    promo_id = int(callback.data.split(":")[3])
    promo = await get_promo_by_id(promo_id, master.id)

    if not promo:
        await callback.answer("Акция не найдена")
        return

    text = (
        f"🎁 {promo.title}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promo.text}\n\n"
        f"📅 {promo.active_from} — {promo.active_to}\n"
        f"👥 Уведомлено клиентов: {promo.sent_count or 0}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, promo_card_kb(promo_id))
    await callback.answer()


@router.callback_query(F.data.startswith("marketing:promo:end:") & ~F.data.contains("confirm"))
async def cb_promo_end(callback: CallbackQuery) -> None:
    """Confirm promo deactivation."""
    promo_id = int(callback.data.split(":")[3])

    text = (
        "❌ Завершить акцию?\n"
        "━━━━━━━━━━━━━━━\n"
        "Акция будет убрана из активных."
    )

    await edit_home_message(callback, text, promo_end_confirm_kb(promo_id))
    await callback.answer()


@router.callback_query(F.data.startswith("marketing:promo:end:confirm:"))
async def cb_promo_end_confirm(callback: CallbackQuery) -> None:
    """Deactivate promo."""
    tg_id = callback.from_user.id
    master = await get_master_by_tg_id(tg_id)

    promo_id = int(callback.data.split(":")[4])
    await deactivate_promo(promo_id, master.id)

    # Return to marketing
    promos = await get_active_promos(master.id)

    if promos:
        promos_text = "Активные акции:\n" + "\n".join(f"• {p.title}" for p in promos)
    else:
        promos_text = "Активных акций нет"

    text = (
        f"📢 Маркетинг\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ Акция завершена\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{promos_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await edit_home_message(callback, text, marketing_kb(promos))
    await callback.answer("Акция завершена")
