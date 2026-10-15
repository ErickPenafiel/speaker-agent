import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, DemoReadOnlyError
from app.core.limits import limiter, panel_limit, write_limit
from app.core.session import SessionId
from app.db.session import get_session
from app.schemas.orders import OrderOut, StatusIn
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[OrderOut])
@limiter.limit(panel_limit)
async def list_orders(
    request: Request,
    session: SessionDep,
    sid: SessionId,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    since: Annotated[datetime | None, Query(description="solo pedidos creados después de")] = None,
):
    return await order_service.list_orders(
        session, session_id=sid, limit=limit, offset=offset, since=since
    )


@router.patch("/{order_id}/status", response_model=OrderOut)
@limiter.limit(write_limit)
async def update_status(
    request: Request, order_id: uuid.UUID, body: StatusIn, session: SessionDep, sid: SessionId
):
    try:
        order = await order_service.update_status(session, order_id, body.status, session_id=sid)
    except DemoReadOnlyError as e:
        raise HTTPException(403, detail="Los pedidos de ejemplo son de solo lectura") from e
    except BusinessError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return order
