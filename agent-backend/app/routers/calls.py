import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limits import limiter, panel_limit
from app.core.session import SessionId
from app.db.session import get_session
from app.schemas.calls import CallDetailOut, CallOut, Outcome
from app.schemas.orders import OrderOut
from app.schemas.reservations import ReservationOut
from app.services import call_service

router = APIRouter(prefix="/calls", tags=["calls"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[CallOut])
@limiter.limit(panel_limit)
async def list_calls(
    request: Request,
    session: SessionDep,
    sid: SessionId,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    outcome: Annotated[Outcome | None, Query()] = None,
    since: Annotated[datetime | None, Query(description="guardadas después de")] = None,
):
    return await call_service.list_calls(
        session, session_id=sid, limit=limit, offset=offset, outcome=outcome, since=since
    )


@router.get("/{call_id}", response_model=CallDetailOut)
@limiter.limit(panel_limit)
async def get_call(request: Request, call_id: uuid.UUID, session: SessionDep, sid: SessionId):
    detail = await call_service.get_detail(session, call_id, session_id=sid)
    if detail is None:
        raise HTTPException(status_code=404, detail="Llamada no encontrada")
    call = detail["call"]
    base = CallOut.model_validate(call)
    return CallDetailOut(
        **{name: getattr(base, name) for name in CallOut.model_fields},
        transcript=call.transcript or [],
        orders=[OrderOut.model_validate(o) for o in detail["orders"]],
        reservations=[ReservationOut.model_validate(r) for r in detail["reservations"]],
        transfers=detail["transfers"],
    )
