import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limits import limiter, panel_limit
from app.core.session import SessionId
from app.db.session import get_session
from app.schemas.reservations import ReservationOut
from app.services import reservation_service

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.get("", response_model=list[ReservationOut])
@limiter.limit(panel_limit)
async def list_reservations(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    sid: SessionId,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    since: Annotated[dt.datetime | None, Query(description="creadas después de")] = None,
    date_from: Annotated[dt.date | None, Query()] = None,
    date_to: Annotated[dt.date | None, Query()] = None,
):
    return await reservation_service.list_reservations(
        session,
        session_id=sid,
        limit=limit,
        offset=offset,
        since=since,
        date_from=date_from,
        date_to=date_to,
    )
