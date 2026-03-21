"""Services endpoint - master's service catalog."""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_client
from src.database import get_services
from src.models import Client, Master, MasterClient

router = APIRouter(tags=["services"])


@router.get("/services")
async def get_services_list(
    data: tuple[Client, Master, MasterClient] = Depends(get_current_client)
):
    """Get master's active services."""
    client, master, master_client = data

    services = await get_services(master.id, active_only=True)

    return [
        {
            "id": service.id,
            "name": service.name,
            "price": service.price,
            "description": service.description,
        }
        for service in services
    ]
