"""Inserción idempotente, común a pedidos, reservas y transferencias."""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


def idempotency_key(
    call_id: str | None, tool_call_id: str | None, args: dict, scope: str = "order"
) -> str | None:
    """Vapi aporta `tool_call_id`; Retell no, así que se deriva de la llamada y los argumentos."""
    if tool_call_id:
        raw = f"{scope}|tc|{tool_call_id}"
    elif call_id:
        raw = f"{scope}|ca|{call_id}|{json.dumps(args, sort_keys=True, default=str)}"
    else:
        return None
    return hashlib.sha256(raw.encode()).hexdigest()[:48]


async def find_by_key[T](session: AsyncSession, model: type[T], key: str) -> T | None:
    return await session.scalar(select(model).where(model.idempotency_key == key))  # type: ignore[attr-defined]


async def insert_once[T](session: AsyncSession, obj: T, model: type[T]) -> tuple[T, bool]:
    """Inserta `obj`; si otra petición con la misma clave ganó la carrera devuelve el existente.
    Usa un savepoint para que el duplicado no aborte la transacción. -> (objeto, creado?)"""
    key = obj.idempotency_key  # type: ignore[attr-defined]
    try:
        async with session.begin_nested():
            session.add(obj)
    except IntegrityError:
        existing = await find_by_key(session, model, key) if key else None
        if existing is None:
            raise
        return existing, False
    return obj, True
