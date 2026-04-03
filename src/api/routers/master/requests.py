"""Master requests — view and manage inbound client requests."""

from fastapi import APIRouter, Depends, HTTPException
from src.api.dependencies import get_current_master
from src.database import get_inbound_requests, mark_request_read, mark_all_requests_read
from src.models import Master

router = APIRouter(tags=["master"])


@router.get("/master/requests")
async def list_requests(master: Master = Depends(get_current_master)):
    """Get all inbound requests for the master."""
    requests = await get_inbound_requests(master.id)
    return {"requests": requests}


@router.put("/master/requests/read-all")
async def read_all_requests(master: Master = Depends(get_current_master)):
    """Mark all requests as read."""
    await mark_all_requests_read(master.id)
    return {"success": True}


@router.put("/master/requests/{request_id}/read")
async def read_request(
    request_id: int,
    master: Master = Depends(get_current_master)
):
    """Mark a single request as read."""
    updated = await mark_request_read(request_id, master.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"success": True}
