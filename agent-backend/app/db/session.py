from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings, is_pooled


def build_engine(url: str, settings: Settings) -> AsyncEngine:
    """Engine async. Con el endpoint pooled de Neon (pgbouncer en modo transacción) hay que
    desactivar la caché de sentencias preparadas, tanto en asyncpg como en SQLAlchemy."""
    parsed = make_url(url)
    connect_args: dict[str, Any] = {"timeout": 15}  # Neon puede tardar al despertar
    pooled = settings.db_pooled if settings.db_pooled is not None else is_pooled(url)
    if pooled:
        connect_args["statement_cache_size"] = 0
        parsed = parsed.update_query_dict({"prepared_statement_cache_size": "0"})
    return create_async_engine(
        parsed,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,  # descarta conexiones que el servidor cerró por inactividad
        pool_recycle=300,
        hide_parameters=True,  # los errores de SQL no deben incluir datos de clientes en logs/Sentry
        connect_args=connect_args,
    )


_settings = get_settings()
engine = build_engine(_settings.database_url, _settings)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
