"""Client profile endpoint."""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_client
from src.models import Client, Master, MasterClient

router = APIRouter(tags=["client"])


@router.get("/me")
async def get_me(
    data: tuple[Client, Master, MasterClient] = Depends(get_current_client)
):
    """Get current client profile with master info and bonus balance."""
    client, master, master_client = data

    return {
        "client": {
            "id": client.id,
            "name": client.name,
            "phone": client.phone,
        },
        "master": {
            "id": master.id,
            "name": master.name,
            "sphere": master.sphere,
            "contacts": master.contacts,
            "socials": master.socials,
            "work_hours": master.work_hours,
        },
        "bonus_balance": master_client.bonus_balance,
    }
