"""Master category dictionary and current-master category links."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from src.api.dependencies import get_current_master
from src.database import (
    get_all_categories,
    get_category_by_slug,
    get_master_categories,
    set_master_categories,
)
from src.models import Master

router = APIRouter(tags=["master-categories"])


class CategoriesUpdateBody(BaseModel):
    category_ids: list[int]
    custom_names: Optional[dict[str, str]] = None

    @field_validator("category_ids")
    @classmethod
    def category_ids_valid(cls, value):
        if not isinstance(value, list) or not (1 <= len(value) <= 3):
            raise ValueError("category_ids must contain 1-3 items")
        if len(set(value)) != len(value):
            raise ValueError("category_ids must be unique")
        return value

    @field_validator("custom_names")
    @classmethod
    def custom_names_valid(cls, value):
        if value is None:
            return value
        for key, text in value.items():
            if not str(key).isdigit():
                raise ValueError("custom_names keys must be category ids")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("custom_names values must be non-empty strings")
            if len(text.strip()) > 100:
                raise ValueError("custom_names values max 100 chars")
        return value


@router.get("/master/categories")
async def list_master_categories():
    """Return public dictionary of active master categories."""
    return {"categories": await get_all_categories()}


@router.get("/master/me/categories")
async def get_current_master_categories(master: Master = Depends(get_current_master)):
    """Return normalized categories for the current master."""
    return {"categories": await get_master_categories(master.id)}


@router.put("/master/me/categories")
async def update_current_master_categories(
    body: CategoriesUpdateBody,
    master: Master = Depends(get_current_master),
):
    """Replace normalized categories for the current master."""
    custom_names = {int(key): value.strip() for key, value in (body.custom_names or {}).items()}
    categories = await get_all_categories()
    active_by_id = {category["id"]: category for category in categories}
    missing = [category_id for category_id in body.category_ids if category_id not in active_by_id]
    if missing:
        raise HTTPException(status_code=422, detail="One or more categories do not exist")

    other = await get_category_by_slug("other")
    other_id = other["id"] if other else None
    if other_id in body.category_ids and not custom_names.get(other_id):
        raise HTTPException(status_code=422, detail="Custom name is required for category 'other'")

    allowed_custom_ids = set(body.category_ids)
    extra_custom_ids = set(custom_names.keys()) - allowed_custom_ids
    if extra_custom_ids:
        raise HTTPException(status_code=422, detail="custom_names contains ids outside category_ids")

    await set_master_categories(master.id, body.category_ids, custom_names)
    return {"categories": await get_master_categories(master.id)}
