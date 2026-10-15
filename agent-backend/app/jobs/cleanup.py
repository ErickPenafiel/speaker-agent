"""Limpieza de datos de visitantes. La sesión demo nunca se borra.

uv run python -m app.jobs.cleanup        # una pasada (útil como cron externo)
"""

import asyncio
import datetime as dt
from collections.abc import Awaitable, Callable

import structlog
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.session import DEMO_SESSION
from app.db.models import Call, Order, Reservation, Transfer
from app.db.session import SessionLocal

log = structlog.get_logger()


async def purge_old(
    session: AsyncSession, retention_days: int, *, now: dt.datetime | None = None
) -> dict[str, int]:
    """Borra lo más viejo que `retention_days` (incluidas filas sin sesión, que nadie puede ver).
    Las líneas de pedido caen por ON DELETE CASCADE."""
    cutoff = (now or dt.datetime.now(dt.UTC)) - dt.timedelta(days=retention_days)
    deleted = {}
    for model in (Order, Reservation, Transfer, Call):
        result = await session.execute(
            delete(model).where(
                model.created_at < cutoff,
                model.session_id.is_distinct_from(DEMO_SESSION),
            )
        )
        deleted[model.__tablename__] = result.rowcount
    await session.commit()
    return deleted


async def cleanup_loop(
    factory: async_sessionmaker[AsyncSession] = SessionLocal,
    *,
    interval_hours: int,
    retention_days: int,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Tarea de fondo: una pasada inmediata y luego cada `interval_hours`. Nunca muere por un error."""
    while True:
        try:
            async with factory() as session:
                deleted = await purge_old(session, retention_days)
            log.info("cleanup_done", **deleted)
        except Exception:
            log.exception("cleanup_failed")
        await sleep(interval_hours * 3600)


async def main() -> None:
    async with SessionLocal() as session:
        print(await purge_old(session, get_settings().data_retention_days))


if __name__ == "__main__":
    asyncio.run(main())
