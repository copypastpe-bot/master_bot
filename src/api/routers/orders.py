"""Orders endpoints - history and order requests."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.api.dependencies import get_current_client
from src.database import get_client_orders, save_inbound_request
from src.models import Client, Master, MasterClient

router = APIRouter(tags=["orders"])

# Master bot instance for sending notifications
_master_bot = None


def set_master_bot(bot):
    """Set master bot instance for notifications."""
    global _master_bot
    _master_bot = bot


class OrderRequest(BaseModel):
    """Order request from Mini App."""
    service_name: str
    master_id: Optional[int] = None  # для мультимастерных клиентов
    comment: Optional[str] = None


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
    request: OrderRequest,
    data: tuple[Client, Master, MasterClient] = Depends(get_current_client)
):
    """Create an order request (inbound request to master)."""
    client, master, master_client = data

    # Save to inbound_requests
    await save_inbound_request(
        master_id=master.id,
        client_id=client.id,
        type="order_request",
        service_name=request.service_name,
        text=request.comment,
    )

    # Send notification to master
    if _master_bot:
        comment_line = f"\n💬 {request.comment}" if request.comment else ""
        phone_line = f"\n📞 {client.phone}" if client.phone else ""

        notification_text = (
            f"🛎 Новая заявка из Mini App!\n\n"
            f"👤 {client.name}{phone_line}\n"
            f"🛠 Услуга: {request.service_name}{comment_line}"
        )

        try:
            await _master_bot.send_message(
                chat_id=master.tg_id,
                text=notification_text
            )
        except Exception:
            # Don't fail the request if notification fails
            pass

    return {"success": True}
