from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.limits import limiter, web_call_cap
from app.db.models import Base
from app.db.session import get_session
from app.main import app

SID = "sess-test-000000001"  # sesión del visitante de pruebas (el cliente la envía por defecto)
OTHER_SID = "sess-test-000000002"


@pytest.fixture(autouse=True)
def _no_rate_limit():
    """Los límites se prueban explícitamente en test_limits.py; en el resto estorbarían."""
    limiter.enabled = False
    limiter.reset()
    web_call_cap.reset()
    yield
    limiter.enabled = True
    limiter.reset()
    web_call_cap.reset()


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_settings().database_url_test)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={"X-Session-Id": SID}
    ) as c:
        yield c
    app.dependency_overrides.clear()
