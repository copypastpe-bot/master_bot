"""Scheduler module for reminders and birthday bonuses."""

import logging
from datetime import datetime
from pathlib import Path
import pytz

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from src.database import (
    get_orders_for_reminder_24h,
    get_orders_for_reminder_1h,
    get_orders_for_feedback,
    get_clients_with_birthday_today,
    mark_reminder_sent,
    mark_feedback_sent,
    accrue_birthday_bonus,
    get_masters_expiring_soon,
    mark_subscription_reminder_sent,
)
from src.utils import (
    render_bonus_message,
    DEFAULT_BIRTHDAY_MESSAGE,
    get_currency_symbol,
    render_feedback_message,
    DEFAULT_FEEDBACK_MESSAGE,
)
from src.config import REMINDER_DAYS_BEFORE

logger = logging.getLogger(__name__)

# Initialize scheduler with Moscow timezone
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]


def confirm_order_kb(order_id: int) -> InlineKeyboardMarkup:
    """Keyboard with confirm/reschedule/cancel buttons for 24h reminder."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтверждаю запись", callback_data=f"confirm_order:{order_id}")],
        [
            InlineKeyboardButton(text="📅 Перенести", callback_data=f"reschedule_order:{order_id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_order:{order_id}"),
        ],
    ])


def write_master_kb(master_tg_id: int) -> InlineKeyboardMarkup:
    """Keyboard with button to write to master for 1h reminder."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Написать мастеру", url=f"tg://user?id={master_tg_id}")]
    ])


def feedback_rating_kb(order_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard with rating buttons 1-5."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=str(i), callback_data=f"feedback:{order_id}:{i}")
            for i in range(1, 6)
        ]
    ])


async def _send_photo_by_ref(bot: Bot, chat_id: int, photo_ref: str, caption: str) -> None:
    """Send photo by file_id/url or local media reference."""
    if photo_ref.startswith("local:"):
        path = Path(photo_ref[len("local:"):]).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Bonus image not found: {path}")
        await bot.send_photo(
            chat_id=chat_id,
            photo=BufferedInputFile(path.read_bytes(), filename=path.name or "bonus.jpg"),
            caption=caption,
        )
        return
    await bot.send_photo(chat_id=chat_id, photo=photo_ref, caption=caption)


async def send_reminders_24h(client_bot: Bot) -> None:
    """Send 24-hour reminders to clients."""
    logger.info("Running 24h reminder task")

    try:
        orders = await get_orders_for_reminder_24h()
        logger.info(f"Found {len(orders)} orders for 24h reminder")

        for order in orders:
            try:
                # Parse scheduled_at
                scheduled_at = datetime.fromisoformat(order["scheduled_at"])
                day = scheduled_at.day
                month = MONTHS_RU[scheduled_at.month]
                time_str = scheduled_at.strftime("%H:%M")

                services = order.get("services") or "—"
                address = order.get("address") or "—"
                master_name = order.get("master_name") or "—"
                master_contacts = order.get("master_contacts") or "—"

                text = (
                    f"🔔 Напоминание о записи\n\n"
                    f"Завтра у вас запись:\n"
                    f"📅 {day} {month}, {time_str}\n"
                    f"📍 {address}\n"
                    f"🛠 {services}\n\n"
                    f"Мастер: {master_name}\n"
                    f"📞 {master_contacts}"
                )

                await client_bot.send_message(
                    chat_id=order["client_tg_id"],
                    text=text,
                    reply_markup=confirm_order_kb(order["order_id"])
                )

                await mark_reminder_sent(order["order_id"], "24h")
                logger.info(f"Sent 24h reminder for order {order['order_id']}")

            except TelegramForbiddenError:
                logger.warning(f"Client {order['client_tg_id']} blocked the bot, skipping")
                await mark_reminder_sent(order["order_id"], "24h")
            except TelegramBadRequest as e:
                logger.error(f"Failed to send 24h reminder for order {order['order_id']}: {e}")
            except Exception as e:
                logger.error(f"Error sending 24h reminder for order {order['order_id']}: {e}")

    except Exception as e:
        logger.error(f"Error in send_reminders_24h: {e}")


async def send_reminders_1h(client_bot: Bot) -> None:
    """Send 1-hour reminders to clients."""
    logger.info("Running 1h reminder task")

    try:
        orders = await get_orders_for_reminder_1h()
        logger.info(f"Found {len(orders)} orders for 1h reminder")

        for order in orders:
            try:
                # Parse scheduled_at
                scheduled_at = datetime.fromisoformat(order["scheduled_at"])
                time_str = scheduled_at.strftime("%H:%M")

                services = order.get("services") or "—"
                address = order.get("address") or "—"
                master_name = order.get("master_name") or "—"
                master_contacts = order.get("master_contacts") or "—"

                text = (
                    f"⏰ Через час ваша запись!\n\n"
                    f"📅 Сегодня в {time_str}\n"
                    f"📍 {address}\n"
                    f"🛠 {services}\n\n"
                    f"Мастер: {master_name}\n"
                    f"📞 {master_contacts}"
                )

                await client_bot.send_message(
                    chat_id=order["client_tg_id"],
                    text=text,
                    reply_markup=write_master_kb(order["master_tg_id"])
                )

                await mark_reminder_sent(order["order_id"], "1h")
                logger.info(f"Sent 1h reminder for order {order['order_id']}")

            except TelegramForbiddenError:
                logger.warning(f"Client {order['client_tg_id']} blocked the bot, skipping")
                await mark_reminder_sent(order["order_id"], "1h")
            except TelegramBadRequest as e:
                logger.error(f"Failed to send 1h reminder for order {order['order_id']}: {e}")
            except Exception as e:
                logger.error(f"Error sending 1h reminder for order {order['order_id']}: {e}")

    except Exception as e:
        logger.error(f"Error in send_reminders_1h: {e}")


async def send_feedback_requests(client_bot: Bot) -> None:
    """Send post-order feedback requests to clients."""
    logger.info("Running feedback request task")
    try:
        orders = await get_orders_for_feedback()
        logger.info("Found %s orders for feedback request", len(orders))

        for order in orders:
            try:
                text = render_feedback_message(
                    template=order.get("feedback_message"),
                    default=DEFAULT_FEEDBACK_MESSAGE,
                    master_name=order.get("master_name") or "мастера",
                    services=order.get("services") or "—",
                )
                await client_bot.send_message(
                    chat_id=order["client_tg_id"],
                    text=text,
                    reply_markup=feedback_rating_kb(order["order_id"]),
                )
                await mark_feedback_sent(order["order_id"])
                logger.info("Sent feedback request for order %s", order["order_id"])
            except TelegramForbiddenError:
                logger.warning("Client %s blocked the bot, skipping", order["client_tg_id"])
                await mark_feedback_sent(order["order_id"])
            except TelegramBadRequest as e:
                logger.error("Failed to send feedback request for order %s: %s", order["order_id"], e)
            except Exception as e:
                logger.error("Error sending feedback request for order %s: %s", order["order_id"], e)
    except Exception as e:
        logger.error("Error in send_feedback_requests: %s", e)


async def send_birthday_bonuses(client_bot: Bot) -> None:
    """Send birthday bonuses to clients at 13:00 in master's timezone."""
    logger.info("Running birthday bonus task")

    try:
        clients = await get_clients_with_birthday_today()
        logger.info(f"Found {len(clients)} clients with birthday today")

        for client in clients:
            try:
                # Check if it's 13:00 in master's timezone
                master_tz_str = client.get("timezone") or "Europe/Moscow"
                try:
                    master_tz = pytz.timezone(master_tz_str)
                except Exception:
                    master_tz = pytz.timezone("Europe/Moscow")

                now_in_master_tz = datetime.now(master_tz)

                # Only send at 13:XX (between 13:00 and 13:59)
                if now_in_master_tz.hour != 13:
                    continue

                # Accrue bonus (with duplicate protection via bonus_log)
                new_balance = await accrue_birthday_bonus(
                    client["master_id"],
                    client["client_id"]
                )

                # If balance didn't change, bonus was already accrued today
                if new_balance == client["bonus_balance"]:
                    logger.info(f"Birthday bonus already accrued for client {client['client_id']}")
                    continue

                bonus_amount = client["bonus_birthday"]
                client_name = client.get("client_name") or "—"
                master_name = client.get("master_name") or "—"
                currency = get_currency_symbol(client.get("currency") or "RUB")

                # Use custom message template if set
                text = render_bonus_message(
                    template=client.get("birthday_message"),
                    default=DEFAULT_BIRTHDAY_MESSAGE,
                    client_name=client_name,
                    master_name=master_name,
                    bonus_amount=bonus_amount,
                    balance=new_balance,
                    currency=currency,
                    welcome_bonus=client.get("bonus_welcome"),
                    birthday_bonus=bonus_amount,
                )

                # Send with photo if set
                birthday_photo_id = client.get("birthday_photo_id")
                if birthday_photo_id:
                    try:
                        await _send_photo_by_ref(
                            bot=client_bot,
                            chat_id=client["client_tg_id"],
                            photo_ref=birthday_photo_id,
                            caption=text,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to send birthday image for client %s, fallback to text: %s",
                            client["client_id"], e,
                        )
                        await client_bot.send_message(
                            chat_id=client["client_tg_id"],
                            text=text,
                        )
                else:
                    await client_bot.send_message(
                        chat_id=client["client_tg_id"],
                        text=text
                    )

                logger.info(f"Sent birthday bonus to client {client['client_id']}: +{bonus_amount}")

            except TelegramForbiddenError:
                logger.warning(f"Client {client['client_tg_id']} blocked the bot, skipping")
            except TelegramBadRequest as e:
                logger.error(f"Failed to send birthday bonus to client {client['client_id']}: {e}")
            except Exception as e:
                logger.error(f"Error sending birthday bonus to client {client['client_id']}: {e}")

    except Exception as e:
        logger.error(f"Error in send_birthday_bonuses: {e}")


async def send_subscription_expiry_reminders(master_bot: Bot) -> None:
    """Send subscription expiry reminders to masters."""
    logger.info("Running subscription expiry reminder task")
    try:
        expiring = await get_masters_expiring_soon(days=REMINDER_DAYS_BEFORE)
        logger.info("Found %s masters with expiring subscriptions", len(expiring))

        for master in expiring:
            try:
                subscription_until = master["subscription_until"]
                expiry_str = subscription_until.strftime("%d.%m.%Y")
                days_left = master.get("days_left", 0)
                text = (
                    f"Ваша подписка истекает через {days_left} дней — {expiry_str}.\n"
                    f"Продлите в приложении."
                )
                await master_bot.send_message(chat_id=master["tg_id"], text=text)
                await mark_subscription_reminder_sent(master["id"])
            except TelegramForbiddenError:
                logger.warning("Master %s blocked bot for reminders", master.get("tg_id"))
            except TelegramBadRequest as e:
                logger.error("Failed to send subscription reminder to %s: %s", master.get("tg_id"), e)
            except Exception as e:
                logger.error("Unexpected reminder error for master %s: %s", master.get("id"), e)
    except Exception as e:
        logger.error("Error in send_subscription_expiry_reminders: %s", e)


def setup_scheduler(client_bot: Bot, master_bot: Bot | None = None) -> None:
    """Setup and start the scheduler with all tasks."""
    # 24h reminder - every 60 minutes
    scheduler.add_job(
        send_reminders_24h,
        "interval",
        minutes=60,
        args=[client_bot],
        id="reminder_24h",
        replace_existing=True
    )

    # 1h reminder - every 15 minutes
    scheduler.add_job(
        send_reminders_1h,
        "interval",
        minutes=15,
        args=[client_bot],
        id="reminder_1h",
        replace_existing=True
    )

    # Birthday bonuses - every 30 minutes to check timezone-aware 13:00
    scheduler.add_job(
        send_birthday_bonuses,
        "interval",
        minutes=30,
        args=[client_bot],
        id="birthday_bonus",
        replace_existing=True
    )

    scheduler.add_job(
        send_feedback_requests,
        "interval",
        minutes=30,
        args=[client_bot],
        id="feedback_request",
        replace_existing=True,
    )

    if master_bot is not None:
        scheduler.add_job(
            send_subscription_expiry_reminders,
            "interval",
            hours=24,
            args=[master_bot],
            id="subscription_expiry_reminder",
            replace_existing=True,
        )

    logger.info("Scheduler jobs configured")


def start_scheduler() -> None:
    """Start the scheduler."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler() -> None:
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
