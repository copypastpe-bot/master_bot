"""Notifications module for sending messages to clients via client_bot."""

import logging
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from src.config import CLIENT_BOT_TOKEN, CLIENT_MINIAPP_URL
from src.database import get_order_notification_context
from src.models import Client, Order, Master
from src.utils import get_currency_symbol

logger = logging.getLogger(__name__)

# Bot instance for sending notifications (no polling)
client_bot = Bot(token=CLIENT_BOT_TOKEN)

MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]


def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    return f"{dt.day} {MONTHS_RU[dt.month]} в {dt.strftime('%H:%M')}"


def _client_miniapp_url(**params: str | int) -> str:
    parts = urlsplit(CLIENT_MINIAPP_URL)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    for key, value in params.items():
        query[key] = str(value)
    return urlunsplit(parts._replace(query=urlencode(query)))


def open_app_button(**params: str | int) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="Открыть приложение",
        web_app=WebAppInfo(url=_client_miniapp_url(**params)),
    )


def order_action_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Связаться", callback_data=f"contact_order:{order_id}"),
            open_app_button(),
        ],
    ])


def reminder_24h_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_order:{order_id}"),
            InlineKeyboardButton(text="Связаться", callback_data=f"contact_order:{order_id}"),
        ],
        [open_app_button()],
    ])


def contact_keyboard(phone: str | None, telegram: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    phone_value = (phone or "").strip()
    telegram_value = (telegram or "").strip().lstrip("@")
    if phone_value:
        rows.append([InlineKeyboardButton(text="Позвонить", url=f"tel:{phone_value}")])
    if telegram_value:
        rows.append([InlineKeyboardButton(text="Написать в TG", url=f"https://t.me/{telegram_value}")])
    rows.append([open_app_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def review_keyboard(order_id: int, master_id: int | None = None) -> InlineKeyboardMarkup:
    params: dict[str, str | int] = {"review_order_id": order_id}
    if master_id is not None:
        params["master_id"] = master_id
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Оставить отзыв",
                web_app=WebAppInfo(url=_client_miniapp_url(**params)),
            )
        ],
    ])


async def notify_order_created(
    client: Client,
    order: dict,
    master: Master,
    services: list[dict],
    bot=None,
) -> bool:
    """Notify client about a new order if reminder notifications are enabled."""
    if not client.tg_id:
        return False

    context = await get_order_notification_context(order["id"], client_tg_id=client.tg_id)
    if not context or not context.get("notify_reminders"):
        return False

    try:
        scheduled_at = order.get("scheduled_at")
        if isinstance(scheduled_at, str):
            scheduled_at = datetime.fromisoformat(scheduled_at)

        services_text = ", ".join(s["name"] for s in services) or "—"
        date_str = f"{scheduled_at.day} {MONTHS_RU[scheduled_at.month]}"
        time_str = scheduled_at.strftime("%H:%M")
        address = (order.get("address") or "").strip()
        text = (
            f"{master.name} записал(а) вас:\n\n"
            f"{services_text}\n"
            f"{date_str}, {time_str}"
        )
        if address:
            text += f"\n{address}"

        await (bot or client_bot).send_message(
            client.tg_id,
            text,
            reply_markup=order_action_keyboard(order["id"]),
        )
        logger.info("Notification sent to client %s: order created", client.id)
        return True

    except TelegramForbiddenError:
        logger.warning("Client %s blocked the bot", client.id)
        return False
    except TelegramBadRequest as e:
        logger.error("Failed to send notification to client %s: %s", client.id, e)
        return False
    except Exception as e:
        logger.error("Unexpected error sending notification to client %s: %s", client.id, e)
        return False


async def notify_manual_bonus(
    chat_id: int,
    master_name: str,
    amount: int,
    comment: str | None,
    balance: int,
    bot=None,
) -> bool:
    """Notify a client about standalone positive manual bonus accrual."""
    if amount <= 0:
        return False

    comment_text = (comment or "").strip()
    text = f"Начислено +{amount} бонусов"
    if comment_text:
        text += f"\n{comment_text}"
    text += f"\nот {master_name}\n\nВаш баланс: {balance} бонусов"

    try:
        await (bot or client_bot).send_message(chat_id=chat_id, text=text)
        return True
    except TelegramForbiddenError:
        logger.warning("Client %s blocked the bot for manual bonus notification", chat_id)
        return False
    except TelegramBadRequest as e:
        logger.error("Failed to send manual bonus notification to %s: %s", chat_id, e)
        return False


async def notify_order_moved(
    client: Client,
    order: dict,
    master: Master,
    old_dt: datetime,
    bot=None,
) -> bool:
    """Notify client that order was rescheduled."""
    if not client.tg_id:
        return False

    try:
        new_dt = order.get("scheduled_at")
        if isinstance(new_dt, str):
            new_dt = datetime.fromisoformat(new_dt)

        text = (
            "📅 Запись перенесена\n"
            "━━━━━━━━━━━━━━━\n"
            f"❌ Было: {format_datetime(old_dt)}\n"
            f"✅ Стало: {format_datetime(new_dt)}\n"
            f"📍 {order.get('address', '—')}\n"
            "━━━━━━━━━━━━━━━\n"
            f"Мастер: {master.name}\n"
            f"📞 {master.contacts or '—'}"
        )

        await (bot or client_bot).send_message(client.tg_id, text)
        logger.info(f"Notification sent to client {client.id}: order moved")
        return True

    except TelegramForbiddenError:
        logger.warning(f"Client {client.id} blocked the bot")
        return False
    except TelegramBadRequest as e:
        logger.error(f"Failed to send notification to client {client.id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending notification to client {client.id}: {e}")
        return False


async def notify_order_cancelled(
    client: Client,
    order: dict,
    master: Master,
    bot=None,
) -> bool:
    """Notify client that order was cancelled."""
    if not client.tg_id:
        return False

    try:
        scheduled_at = order.get("scheduled_at")
        if isinstance(scheduled_at, str):
            scheduled_at = datetime.fromisoformat(scheduled_at)

        services = order.get("services", "—")
        cancel_reason = order.get("cancel_reason")

        text = (
            "❌ Запись отменена\n"
            "━━━━━━━━━━━━━━━\n"
            f"📅 {format_datetime(scheduled_at)}\n"
            f"🛠 {services}\n"
        )

        if cancel_reason:
            text += f"📝 Причина: {cancel_reason}\n"

        text += (
            "━━━━━━━━━━━━━━━\n"
            f"Мастер: {master.name}\n"
            f"📞 {master.contacts or '—'}"
        )

        await (bot or client_bot).send_message(client.tg_id, text)
        logger.info(f"Notification sent to client {client.id}: order cancelled")
        return True

    except TelegramForbiddenError:
        logger.warning(f"Client {client.id} blocked the bot")
        return False
    except TelegramBadRequest as e:
        logger.error(f"Failed to send notification to client {client.id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending notification to client {client.id}: {e}")
        return False


async def notify_order_done(
    client: Client,
    order: dict,
    master: Master,
    bonus_accrued: int,
    new_balance: int,
    bot=None,
) -> bool:
    """Notify client that order was completed."""
    if not client.tg_id:
        return False

    try:
        services = order.get("services", "—")
        amount = order.get("amount_total", 0)
        bonus_spent = order.get("bonus_spent", 0)
        curr = get_currency_symbol(master.currency)

        text = (
            "✅ Заказ выполнен!\n"
            "━━━━━━━━━━━━━━━\n"
            f"🛠 {services}\n"
            f"💰 Сумма: {amount} {curr}\n"
        )

        if bonus_spent > 0:
            text += f"🎁 Списано бонусов: {bonus_spent} {curr}\n"

        if bonus_accrued > 0:
            text += f"⭐ Начислено бонусов: +{bonus_accrued} {curr}\n"

        text += (
            f"💳 Ваш баланс: {new_balance} {curr}\n"
            "━━━━━━━━━━━━━━━\n"
            "Спасибо, что выбираете нас!"
        )

        await (bot or client_bot).send_message(client.tg_id, text)
        logger.info(f"Notification sent to client {client.id}: order done")
        return True

    except TelegramForbiddenError:
        logger.warning(f"Client {client.id} blocked the bot")
        return False
    except TelegramBadRequest as e:
        logger.error(f"Failed to send notification to client {client.id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending notification to client {client.id}: {e}")
        return False
