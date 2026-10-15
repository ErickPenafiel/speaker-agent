import difflib
import unicodedata
import uuid
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import BusinessError, DemoReadOnlyError
from app.core.money import format_money
from app.core.session import DEMO_SESSION
from app.db.models import MenuItem, Order, OrderItem
from app.schemas.orders import ALLOWED_TRANSITIONS, CreateOrderArgs, OrderStatus
from app.services.idempotency import find_by_key, idempotency_key, insert_once
from app.services.scope import visible_session


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def resolve_menu_item(menu: list[MenuItem], *, item_id: uuid.UUID | None, name: str | None):
    """Plato por id, o por nombre (exacto, parcial o con errata). Ambigüedad -> BusinessError."""
    if item_id:
        found = next((m for m in menu if m.id == item_id), None)
        if found:
            return found
        if not name:
            raise BusinessError("No encontré ese plato en el menú.")
    q = _norm(name or "")
    exact = [m for m in menu if _norm(m.name) == q]
    if exact:
        return exact[0]
    q_tokens = set(q.split())
    partial = [
        m
        for m in menu
        if q in _norm(m.name) or _norm(m.name) in q or q_tokens <= set(_norm(m.name).split())
    ]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        options = ", ".join(m.name for m in partial[:4])
        raise BusinessError(f"Hay varias opciones para {name}: {options}. Pregunta cuál quiere.")
    close = difflib.get_close_matches(q, [_norm(m.name) for m in menu], n=2, cutoff=0.8)
    if len(close) == 1:
        return next(m for m in menu if _norm(m.name) == close[0])
    raise BusinessError(f"No encontré {name} en el menú.")


def _summary(order: Order, *, duplicate: bool) -> str:
    total = format_money(order.total)
    if duplicate:
        return f"El pedido {order.number} ya estaba registrado. Total {total}."
    s = get_settings()
    minutes = s.prep_minutes_delivery if order.type == "delivery" else s.prep_minutes_pickup
    return (
        f"Pedido {order.number} confirmado. Total {total}. Estará listo en unos {minutes} minutos."
    )


async def create_order_tool(
    session: AsyncSession,
    args: dict,
    *,
    call_id: str | None = None,
    tool_call_id: str | None = None,
    session_id: str | None = None,
) -> str:
    try:
        data = CreateOrderArgs(**args)
    except (ValidationError, TypeError):
        raise BusinessError(
            "Me faltan datos del pedido. Pregunta el nombre y los platos."
        ) from None

    key = idempotency_key(call_id, tool_call_id, args)
    if key and (existing := await find_by_key(session, Order, key)):
        return _summary(existing, duplicate=True)

    if not data.customer_confirmed:
        raise BusinessError("Antes de registrar, resume el pedido y pide confirmación al cliente.")
    if data.type == "delivery" and not (data.address and data.address.strip()):
        raise BusinessError("Para delivery necesito la dirección.")

    menu = list((await session.scalars(select(MenuItem))).all())
    lines: list[OrderItem] = []
    total = Decimal(0)
    for it in data.items:
        item = resolve_menu_item(menu, item_id=it.id, name=it.name)
        if not item.available:
            raise BusinessError(f"{item.name} está agotado.")
        total += item.price * it.quantity
        lines.append(
            OrderItem(
                menu_item_id=item.id,
                name=item.name,
                unit_price=item.price,
                quantity=it.quantity,
                options=it.options,
                notes=it.notes,
            )
        )

    order = Order(
        session_id=session_id,
        call_id=call_id,
        customer_name=data.customer_name.strip(),
        type=data.type,
        address=data.address.strip() if data.address else None,
        status=OrderStatus.confirmed.value,
        notes=data.notes,
        total=total,
        idempotency_key=key,
        items=lines,
    )
    order, created = await insert_once(session, order, Order)
    return _summary(order, duplicate=not created)


async def list_orders(
    session: AsyncSession, *, session_id: str, limit: int, offset: int, since=None
) -> list[Order]:
    owner = await visible_session(session, Order, session_id)
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.session_id == owner)
        .order_by(Order.created_at.desc())
    )
    if since is not None:
        stmt = stmt.where(Order.created_at > since)
    return list((await session.scalars(stmt.limit(limit).offset(offset))).all())


async def update_status(
    session: AsyncSession, order_id: uuid.UUID, new: OrderStatus, *, session_id: str
) -> Order | None:
    """None si no existe o es de otro visitante (404). Datos de ejemplo -> DemoReadOnlyError.
    Transición inválida -> BusinessError. Mismo estado = idempotente."""
    order = await session.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if order is None or order.session_id not in (session_id, DEMO_SESSION):
        return None
    if order.session_id == DEMO_SESSION:
        raise DemoReadOnlyError
    current = OrderStatus(order.status)
    if new != current:
        if new not in ALLOWED_TRANSITIONS[current]:
            raise BusinessError(f"No se puede pasar de {current.value} a {new.value}.")
        order.status = new.value
        await session.commit()
    return order
