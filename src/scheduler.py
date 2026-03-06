"""Scheduler module for reminders and birthday bonuses."""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from src.database import (
    get_orders_for_reminder_24h,
    get_orders_for_reminder_1h,
    get_clients_with_birthday_today,
    mark_reminder_sent,
    accrue_birthday_bonus,
)

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


async def send_birthday_bonuses(client_bot: Bot) -> None:
    """Send birthday bonuses to clients."""
    logger.info("Running birthday bonus task")

    try:
        clients = await get_clients_with_birthday_today()
        logger.info(f"Found {len(clients)} clients with birthday today")

        for client in clients:
            try:
                # Accrue bonus (with duplicate protection)
                new_balance = await accrue_birthday_bonus(
                    client["master_id"],
                    client["client_id"]
                )

                # If balance didn't change, bonus was already accrued
                if new_balance == client["bonus_balance"]:
                    logger.info(f"Birthday bonus already accrued for client {client['client_id']}")
                    continue

                bonus_amount = client["bonus_birthday"]
                client_name = client.get("client_name") or "—"
                master_name = client.get("master_name") or "—"

                text = (
                    f"🎂 С днём рождения, {client_name}!\n\n"
                    f"Ваш мастер {master_name} дарит вам\n"
                    f"🎁 {bonus_amount} бонусов!\n\n"
                    f"💰 Ваш баланс: {new_balance} ₽\n\n"
                    f"Используйте бонусы при следующем заказе."
                )

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


def setup_scheduler(client_bot: Bot) -> None:
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

    # Birthday bonuses - daily at 10:00
    scheduler.add_job(
        send_birthday_bonuses,
        "cron",
        hour=10,
        minute=0,
        args=[client_bot],
        id="birthday_bonus",
        replace_existing=True
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
