"""Telegram Stars payment handlers for master subscription."""

import logging

from aiogram import Bot, F, Router
from aiogram.types import Message, PreCheckoutQuery

from src.config import SUBSCRIPTION_PLANS
from src.database import apply_payment, get_master_by_tg_id
from src.subscription_stars import parse_invoice_payload

logger = logging.getLogger(__name__)

router = Router(name="payments")


@router.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery, bot: Bot) -> None:
    """Accept Telegram pre-checkout query for Stars payments."""
    await bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message) -> None:
    """Apply subscription payment strictly from Telegram successful_payment."""
    payment = message.successful_payment
    if payment is None or message.from_user is None:
        return

    if payment.currency != "XTR":
        logger.warning(
            "Skip non-XTR payment: tg_id=%s currency=%s payload=%s",
            message.from_user.id,
            payment.currency,
            payment.invoice_payload,
        )
        await message.answer("Платеж не обработан: неверная валюта. Напишите в поддержку.")
        return

    parsed = parse_invoice_payload(payment.invoice_payload)
    if parsed is None:
        logger.warning(
            "Skip payment with invalid invoice payload: tg_id=%s payload=%s",
            message.from_user.id,
            payment.invoice_payload,
        )
        await message.answer("Платеж получен, но не прошел проверку. Напишите в поддержку.")
        return

    if parsed.plan_payload not in SUBSCRIPTION_PLANS:
        logger.warning(
            "Skip payment with unknown plan payload: tg_id=%s payload=%s",
            message.from_user.id,
            parsed.plan_payload,
        )
        await message.answer("Платеж получен, но не прошел проверку тарифа. Напишите в поддержку.")
        return

    master = await get_master_by_tg_id(message.from_user.id)
    if master is None:
        logger.warning("Skip payment from unknown master: tg_id=%s", message.from_user.id)
        await message.answer("Платеж получен, но аккаунт мастера не найден. Напишите в поддержку.")
        return

    if master.id != parsed.master_id:
        logger.warning(
            "Skip payment due to master mismatch: payer_master_id=%s payload_master_id=%s",
            master.id,
            parsed.master_id,
        )
        await message.answer("Платеж получен, но не прошел проверку аккаунта. Напишите в поддержку.")
        return

    plan = SUBSCRIPTION_PLANS[parsed.plan_payload]
    expected_stars = int(plan["stars"])
    paid_stars = int(payment.total_amount or 0)
    if paid_stars != expected_stars:
        logger.warning(
            "Skip payment due to amount mismatch: master_id=%s payload=%s paid=%s expected=%s",
            master.id,
            parsed.plan_payload,
            paid_stars,
            expected_stars,
        )
        await message.answer("Платеж получен, но сумма не совпала с тарифом. Напишите в поддержку.")
        return

    charge_id = (
        (payment.telegram_payment_charge_id or "").strip()
        or (payment.provider_payment_charge_id or "").strip()
    )
    if not charge_id:
        logger.warning("Skip payment without charge id: master_id=%s", master.id)
        await message.answer("Платеж получен, но идентификатор платежа отсутствует. Напишите в поддержку.")
        return

    try:
        result = await apply_payment(
            master_id=master.id,
            telegram_charge_id=charge_id,
            payload=parsed.plan_payload,
            stars_amount=paid_stars,
        )
    except Exception:
        logger.exception(
            "Failed to apply Stars payment: master_id=%s payload=%s charge_id=%s",
            master.id,
            parsed.plan_payload,
            charge_id,
        )
        await message.answer("Оплата получена, но не применена автоматически. Напишите в поддержку.")
        return

    if result["duplicate"]:
        await message.answer("Платеж уже был учтен ранее.")
        return

    subscription_until = result["subscription_until"]
    until_text = subscription_until.strftime("%d.%m.%Y") if subscription_until else "—"
    await message.answer(
        "Оплата получена ✅\n"
        f"Подписка продлена на {result['days_added']} дней.\n"
        f"Действует до {until_text}."
    )
