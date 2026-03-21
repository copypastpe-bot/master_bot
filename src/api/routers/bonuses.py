"""Bonuses endpoint - balance and log."""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_client
from src.database import get_client_bonus_log
from src.models import Client, Master, MasterClient

router = APIRouter(tags=["bonuses"])


@router.get("/bonuses")
async def get_bonuses(
    data: tuple[Client, Master, MasterClient] = Depends(get_current_client)
):
    """Get client's bonus balance and transaction log."""
    client, master, master_client = data

    log = await get_client_bonus_log(master.id, client.id, limit=20)

    return {
        "balance": master_client.bonus_balance,
        "log": [
            {
                "id": entry["id"],
                "type": entry["type"],
                "amount": entry["amount"],
                "comment": entry["comment"],
                "created_at": entry["created_at"],
            }
            for entry in log
        ],
    }
