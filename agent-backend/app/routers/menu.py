from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.menu import MenuItemOut
from app.services import menu_service

router = APIRouter(tags=["menu"])


@router.get("/menu", response_model=list[MenuItemOut])
async def get_menu(
    session: Annotated[AsyncSession, Depends(get_session)],
    category: Annotated[str | None, Query()] = None,
) -> list[MenuItemOut]:
    return await menu_service.list_items(session, category)  # type: ignore[return-value]
