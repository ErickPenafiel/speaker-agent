import uuid

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.session import DEMO_SESSION
from app.db.models import Call, Order, Reservation, Transfer
from app.schemas.call_report import CallReport
from app.services.scope import visible_session

log = structlog.get_logger()

OUTCOMES = ("order", "reservation", "transferred", "info", "abandoned")


def derive_outcome(
    transcript: list[dict[str, str]] | None, *, orders: int, reservations: int, transfers: int
) -> str:
    """Resultado de la llamada según lo que realmente quedó guardado (no según el LLM).
    Prioridad: pedido > reserva > transferida > info; sin ningún turno del cliente = abandonada."""
    if orders:
        return "order"
    if reservations:
        return "reservation"
    if transfers:
        return "transferred"
    if any(t["role"] == "user" for t in transcript or []):
        return "info"
    return "abandoned"


async def _count(session: AsyncSession, model, call_id: str) -> int:
    return (
        await session.scalar(
            select(func.count()).select_from(model).where(model.call_id == call_id)
        )
        or 0
    )


async def save_report(session: AsyncSession, report: CallReport) -> Call:
    """Upsert por (provider, provider_call_id). Idempotente y apto para eventos parciales:
    un campo None no pisa el valor guardado (call_ended y call_analyzed se fusionan en cualquier orden)."""
    values = {
        "provider": report.provider,
        "provider_call_id": report.provider_call_id,
        "session_id": report.session_id,
        "started_at": report.started_at,
        "duration_seconds": report.duration_seconds,
        "transcript": report.transcript,
        "summary": report.summary,
    }
    stmt = insert(Call).values(**values)
    merge = ("session_id", "started_at", "duration_seconds", "transcript", "summary")
    stmt = stmt.on_conflict_do_update(
        constraint="uq_calls_provider_call",
        set_={c: func.coalesce(stmt.excluded[c], Call.__table__.c[c]) for c in merge},
    ).returning(Call.id)
    call_id = (await session.execute(stmt)).scalar_one()
    call = await session.get(Call, call_id, populate_existing=True)

    pid = report.provider_call_id
    orders = await _count(session, Order, pid)
    reservations = await _count(session, Reservation, pid)
    transfers = await _count(session, Transfer, pid)
    call.outcome = derive_outcome(
        call.transcript, orders=orders, reservations=reservations, transfers=transfers
    )
    if call.session_id is None:  # la llamada no trajo metadata: usar la de lo que se creó en ella
        for model in (Order, Reservation, Transfer):
            sid = await session.scalar(
                select(model.session_id).where(model.call_id == pid, model.session_id.is_not(None))
            )
            if sid:
                call.session_id = sid
                break
    await session.commit()
    log.info(
        "call_report_saved",
        provider=report.provider,
        call_id=pid,
        outcome=call.outcome,
        duration_s=call.duration_seconds,
        has_transcript=call.transcript is not None,
        has_summary=call.summary is not None,
    )
    return call


async def list_calls(
    session: AsyncSession,
    *,
    session_id: str,
    limit: int,
    offset: int,
    outcome: str | None = None,
    since=None,
) -> list[Call]:
    owner = await visible_session(session, Call, session_id)
    stmt = (
        select(Call)
        .where(Call.session_id == owner)
        .order_by(func.coalesce(Call.started_at, Call.created_at).desc())
    )
    if outcome:
        stmt = stmt.where(Call.outcome == outcome)
    if since is not None:
        stmt = stmt.where(Call.created_at > since)
    return list((await session.scalars(stmt.limit(limit).offset(offset))).all())


async def get_detail(session: AsyncSession, call_id: uuid.UUID, *, session_id: str) -> dict | None:
    """None (404) si no existe o es de otro visitante; las llamadas de ejemplo son públicas."""
    call = await session.get(Call, call_id)
    if call is None or call.session_id not in (session_id, DEMO_SESSION):
        return None
    pid = call.provider_call_id
    orders = await session.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.call_id == pid)
        .order_by(Order.created_at)
    )
    reservations = await session.scalars(
        select(Reservation).where(Reservation.call_id == pid).order_by(Reservation.created_at)
    )
    transfers = await session.scalars(
        select(Transfer).where(Transfer.call_id == pid).order_by(Transfer.created_at)
    )
    return {
        "call": call,
        "orders": list(orders.all()),
        "reservations": list(reservations.all()),
        "transfers": list(transfers.all()),
    }
