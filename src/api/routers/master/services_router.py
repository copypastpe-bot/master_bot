"""Master services endpoint — active services list."""

import logging

from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_master
from src.database import get_services
from src.models import Master

logger = logging.getLogger(__name__)

router = APIRouter(tags=["master"])


@router.get("/master/services")
async def get_master_services(
    master: Master = Depends(get_current_master),
):
    """Get active services for the master."""
    services = await get_services(master.id, active_only=True)
    return {
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "price": s.price or 0,
                "description": s.description or "",
            }
            for s in services
        ]
    }
