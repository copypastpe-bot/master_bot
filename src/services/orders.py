"""Order service layer — shared logic for bot and API."""

import logging
from datetime import datetime
from typing import Optional, Any

from src.database import (
    get_order_by_id,
    get_master_client,
    get_client_by_id,
    update_order_status,
    update_order_schedule,
    apply_bonus_transaction,
)
from src import notifications
from src import google_calendar

logger = logging.getLogger(__name__)


async def complete_order_service(
    order_id: int,
    master,  # Master dataclass instance
    amount: int,
    payment_type: str,
    bonus_spent: int,
    bot=None,  # aiogram Bot instance (optional, for notifications)
) -> dict:
    """
    Complete an order. Handles bonus logic, GC cleanup, and client notification.

    Returns dict with: bonus_accrued, bonus_spent, new_balance, updated_order
    Raises ValueError on validation errors.
    """
    order = await get_order_by_id(order_id, master.id)
    if not order:
        raise ValueError("Order not found")

    status = order.get("status")
    if status not in ("new", "confirmed"):
        raise ValueError(f"Cannot complete order with status '{status}'")

    client_id = order.get("client_id")

    # Validate bonus_spent
    if bonus_spent > 0:
        mc = await get_master_client(master.id, client_id)
        client_balance = mc.bonus_balance if mc else 0
        if bonus_spent > client_balance:
            raise ValueError(
                f"bonus_spent ({bonus_spent}) exceeds client balance ({client_balance})"
            )
        # Also check master's max_spend constraint
        if master.bonus_max_spend:
            max_by_percent = int(amount * master.bonus_max_spend / 100)
            if bonus_spent > max_by_percent:
                raise ValueError(
                    f"bonus_spent ({bonus_spent}) exceeds allowed max "
                    f"({max_by_percent} = {master.bonus_max_spend}% of {amount})"
                )

    # Calculate bonus accrual: applied on amount_paid (amount - bonus_spent)
    amount_paid = amount - bonus_spent
    bonus_accrued = 0
    if master.bonus_enabled and master.bonus_rate:
        bonus_accrued = round(amount_paid * master.bonus_rate / 100)

    # Update order status atomically — guard ensures concurrent complete is rejected
    updated = await update_order_status(
        order_id,
        "done",
        required_statuses=("new", "confirmed"),
        amount_total=amount,
        bonus_spent=bonus_spent,
        bonus_accrued=bonus_accrued,
        payment_type=payment_type,
        done_at=datetime.now().isoformat(),
    )
    if not updated:
        raise ValueError("Order already completed or status changed concurrently")

    # Apply bonus transaction (spend + accrue)
    new_balance = 0
    if bonus_spent > 0 or bonus_accrued > 0:
        new_balance, _ = await apply_bonus_transaction(
            master.id, client_id, order_id, bonus_spent, bonus_accrued
        )
    else:
        mc = await get_master_client(master.id, client_id)
        new_balance = mc.bonus_balance if mc else 0

    # GC: delete event if exists
    gc_event_id = order.get("gc_event_id")
    if gc_event_id:
        try:
            await google_calendar.delete_event(master.id, gc_event_id)
        except Exception as e:
            logger.warning(f"GC delete_event failed (order {order_id}): {e}")

    # Notify client via client_bot
    client = await get_client_by_id(client_id)
    if client and client.tg_id:
        try:
            await notifications.notify_order_done(
                client=client,
                order={
                    "services": order.get("services", ""),
                    "amount_total": amount,
                    "bonus_spent": bonus_spent,
                },
                master=master,
                bonus_accrued=bonus_accrued,
                new_balance=new_balance,
                bot=bot,
            )
        except Exception as e:
            logger.error(f"Failed to notify client (order {order_id}): {e}")

    # Re-fetch updated order
    updated_order = await get_order_by_id(order_id, master.id)

    return {
        "bonus_accrued": bonus_accrued,
        "bonus_spent": bonus_spent,
        "new_balance": new_balance,
        "updated_order": updated_order,
    }


async def move_order_service(
    order_id: int,
    master,
    new_date: str,
    new_time: str,
    bot=None,
) -> dict:
    """
    Move an order to a new date/time. Notifies client.

    Returns dict with: updated_order
    Raises ValueError on validation errors.
    """
    order = await get_order_by_id(order_id, master.id)
    if not order:
        raise ValueError("Order not found")

    status = order.get("status")
    if status not in ("new", "confirmed"):
        raise ValueError(f"Cannot move order with status '{status}'")

    # Parse new datetime
    try:
        new_scheduled_at = datetime.fromisoformat(f"{new_date}T{new_time}:00")
    except ValueError:
        raise ValueError("Invalid date or time format")

    old_dt_str = order.get("scheduled_at")
    old_dt = datetime.fromisoformat(old_dt_str) if old_dt_str else datetime.now()

    await update_order_schedule(order_id, new_scheduled_at)

    # Notify client
    client_id = order.get("client_id")
    client = await get_client_by_id(client_id)
    if client and client.tg_id:
        try:
            updated_order_for_notif = await get_order_by_id(order_id, master.id)
            await notifications.notify_order_moved(
                client=client,
                order=updated_order_for_notif,
                master=master,
                old_dt=old_dt,
                bot=bot,
            )
        except Exception as e:
            logger.error(f"Failed to notify client (order move {order_id}): {e}")

    updated_order = await get_order_by_id(order_id, master.id)
    return {"updated_order": updated_order}


async def cancel_order_service(
    order_id: int,
    master,
    reason: Optional[str] = None,
    bot=None,
) -> dict:
    """
    Cancel an order. Notifies client.

    Returns dict with: updated_order
    Raises ValueError on validation errors.
    """
    order = await get_order_by_id(order_id, master.id)
    if not order:
        raise ValueError("Order not found")

    status = order.get("status")
    if status in ("done", "cancelled"):
        raise ValueError(f"Cannot cancel order with status '{status}'")

    kwargs: dict[str, Any] = {}
    if reason:
        kwargs["cancel_reason"] = reason

    await update_order_status(order_id, "cancelled", **kwargs)

    # GC: delete event if exists
    gc_event_id = order.get("gc_event_id")
    if gc_event_id:
        try:
            await google_calendar.delete_event(master.id, gc_event_id)
        except Exception as e:
            logger.warning(f"GC delete_event failed (cancel order {order_id}): {e}")

    # Notify client
    client_id = order.get("client_id")
    client = await get_client_by_id(client_id)
    if client and client.tg_id:
        try:
            cancelled_order = {**order}
            if reason:
                cancelled_order["cancel_reason"] = reason
            await notifications.notify_order_cancelled(
                client=client,
                order=cancelled_order,
                master=master,
                bot=bot,
            )
        except Exception as e:
            logger.error(f"Failed to notify client (order cancel {order_id}): {e}")

    updated_order = await get_order_by_id(order_id, master.id)
    return {"updated_order": updated_order}
