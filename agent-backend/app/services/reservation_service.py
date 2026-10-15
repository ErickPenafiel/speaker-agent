import datetime as dt
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import BusinessError
from app.db.models import Reservation
from app.schemas.reservations import CreateReservationArgs
from app.services.idempotency import find_by_key, idempotency_key, insert_once
from app.services.scope import visible_session

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip
SLOT = dt.timedelta(minutes=30)


def _now() -> dt.datetime:
    """Hora local del restaurante (naive). Los tests lo reemplazan."""
    return dt.datetime.now(ZoneInfo(get_settings().timezone)).replace(tzinfo=None)


def _hhmm(value: str) -> dt.time:
    return dt.time.fromisoformat(value)


def _say_time(t: dt.time) -> str:
    return t.strftime("%H:%M")


def _say_date(d: dt.date, today: dt.date) -> str:
    if d == today:
        return "hoy"
    if d == today + dt.timedelta(days=1):
        return "mañana"
    return f"el {DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def _round_up(value: dt.datetime) -> dt.datetime:
    value = value.replace(second=0, microsecond=0)
    extra = (value.minute % 30) and (30 - value.minute % 30)
    return value + dt.timedelta(minutes=extra)


def _bounds(s: Settings) -> tuple[dt.time, dt.time]:
    """(primera hora, última hora de reserva) = apertura y cierre menos el margen."""
    open_t = _hhmm(s.restaurant_open)
    close = dt.datetime.combine(dt.date.min, _hhmm(s.restaurant_close))
    last = close - dt.timedelta(minutes=s.reservation_last_seating_minutes_before_close)
    return open_t, last.time()


def _next_slot(now: dt.datetime, s: Settings) -> dt.datetime:
    """Primer horario posible desde ahora respetando margen y horario de atención."""
    open_t, last_t = _bounds(s)
    cand = _round_up(now + dt.timedelta(minutes=s.reservation_min_lead_minutes))
    if cand.time() < open_t:
        return dt.datetime.combine(cand.date(), open_t)
    if cand.time() > last_t or cand.date() > now.date():
        return dt.datetime.combine(cand.date() + dt.timedelta(days=1), open_t)
    return cand


def _ask(alt: dt.datetime, today: dt.date) -> str:
    return f"¿Le sirve {_say_date(alt.date(), today)} a las {_say_time(alt.time())}?"


def validate_slot(when: dt.datetime, party: int, now: dt.datetime, s: Settings) -> None:
    """Lanza BusinessError con un mensaje corto y, si se puede, una alternativa."""
    if party > s.max_party_size:
        raise BusinessError(
            f"Para más de {s.max_party_size} personas no puedo reservar por aquí. "
            "Ofrece pasar con una persona."
        )
    today = now.date()
    if when.date() > today + dt.timedelta(days=s.reservation_max_days_ahead):
        raise BusinessError(
            f"Solo reservamos hasta {s.reservation_max_days_ahead} días por adelantado. "
            "Pregunta por una fecha más cercana."
        )
    open_t, last_t = _bounds(s)
    earliest = now + dt.timedelta(minutes=s.reservation_min_lead_minutes)
    if when < earliest:
        raise BusinessError(f"Esa hora ya pasó o es muy pronto. {_ask(_next_slot(now, s), today)}")
    if not (open_t <= when.time() <= last_t):
        # Mismo día, hora válida más cercana; si ya no hay margen hoy, el siguiente horario libre.
        clamped = dt.datetime.combine(when.date(), open_t if when.time() < open_t else last_t)
        alt = clamped if clamped >= earliest else _next_slot(now, s)
        raise BusinessError(
            f"Atendemos de {_say_time(open_t)} a {s.restaurant_close}; la última reserva es a las "
            f"{_say_time(last_t)}. {_ask(alt, today)}"
        )


def _summary(r: Reservation, today: dt.date, *, duplicate: bool) -> str:
    detail = (
        f"{r.party_size} {'persona' if r.party_size == 1 else 'personas'} "
        f"{_say_date(r.date, today)} a las {_say_time(r.time)} a nombre de {r.customer_name}"
    )
    if duplicate:
        return f"La reserva para {detail} ya estaba registrada."
    return f"Reserva confirmada para {detail}."


async def create_reservation_tool(
    session: AsyncSession,
    args: dict,
    *,
    call_id: str | None = None,
    tool_call_id: str | None = None,
    session_id: str | None = None,
) -> str:
    try:
        data = CreateReservationArgs(**args)
    except (ValidationError, TypeError):
        raise BusinessError(
            "Me faltan datos de la reserva. Pregunta nombre, personas, fecha y hora."
        ) from None

    s = get_settings()
    now = _now()
    key = idempotency_key(call_id, tool_call_id, args, scope="reservation")
    if key and (existing := await find_by_key(session, Reservation, key)):
        return _summary(existing, now.date(), duplicate=True)

    validate_slot(dt.datetime.combine(data.date, data.time), data.party_size, now, s)

    reservation = Reservation(
        session_id=session_id,
        call_id=call_id,
        customer_name=data.customer_name.strip(),
        party_size=data.party_size,
        date=data.date,
        time=data.time.replace(second=0, microsecond=0),
        notes=data.notes,
        idempotency_key=key,
    )
    reservation, created = await insert_once(session, reservation, Reservation)
    return _summary(reservation, now.date(), duplicate=not created)


async def list_reservations(
    session: AsyncSession,
    *,
    session_id: str,
    limit: int,
    offset: int,
    since: dt.datetime | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> list[Reservation]:
    owner = await visible_session(session, Reservation, session_id)
    stmt = (
        select(Reservation)
        .where(Reservation.session_id == owner)
        .order_by(Reservation.date, Reservation.time, Reservation.created_at)
    )
    if since is not None:
        stmt = stmt.where(Reservation.created_at > since)
    if date_from is not None:
        stmt = stmt.where(Reservation.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Reservation.date <= date_to)
    return list((await session.scalars(stmt.limit(limit).offset(offset))).all())
