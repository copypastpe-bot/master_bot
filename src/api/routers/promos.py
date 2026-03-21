"""Promos endpoint - active promotions."""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_client
from src.database import get_active_campaigns
from src.models import Client, Master, MasterClient

router = APIRouter(tags=["promos"])


@router.get("/promos")
async def get_promos(
    data: tuple[Client, Master, MasterClient] = Depends(get_current_client)
):
    """Get active promotions for the master."""
    client, master, master_client = data

    campaigns = await get_active_campaigns(master.id)

    return [
        {
            "id": campaign.id,
            "title": campaign.title,
            "text": campaign.text,
            "active_from": campaign.active_from,
            "active_to": campaign.active_to,
        }
        for campaign in campaigns
    ]
