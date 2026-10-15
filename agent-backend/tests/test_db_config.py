import pytest

from app.core.config import Settings, is_pooled, normalize_database_url
from app.db.session import build_engine

NEON = "postgresql://neon_user:p%40ss%2Fw@ep-cool-123-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"


def test_neon_url_is_converted_for_asyncpg():
    url = normalize_database_url(NEON)
    assert (
        url
        == "postgresql+asyncpg://neon_user:p%40ss%2Fw@ep-cool-123-pooler.us-east-2.aws.neon.tech/neondb?ssl=require"
    )


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("postgres://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        ("postgresql://u:p@h/db?sslmode=disable", "postgresql+asyncpg://u:p@h/db?ssl=disable"),
        ("postgresql+asyncpg://u:p@h/db?ssl=require", "postgresql+asyncpg://u:p@h/db?ssl=require"),
        (
            "postgresql://u:p@h/db?ssl=verify-full&sslmode=require",
            "postgresql+asyncpg://u:p@h/db?ssl=verify-full",
        ),
        ("postgresql+psycopg://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        ("sqlite+aiosqlite:///x.db", "sqlite+aiosqlite:///x.db"),
    ],
)
def test_normalize_cases(raw, want):
    assert normalize_database_url(raw) == want


def test_settings_normalize_all_three_urls():
    s = Settings(
        database_url=NEON, database_url_test=NEON, database_url_direct=NEON.replace("-pooler", "")
    )
    assert (
        s.database_url.startswith("postgresql+asyncpg://")
        and "channel_binding" not in s.database_url
    )
    assert s.database_url_test.startswith("postgresql+asyncpg://")
    assert (
        s.database_url_direct.startswith("postgresql+asyncpg://")
        and "-pooler" not in s.database_url_direct
    )
    assert Settings(database_url_direct="").database_url_direct == ""  # vacío se respeta


def test_pooled_detection():
    assert is_pooled("postgresql://u:p@ep-x-pooler.neon.tech/db")
    assert not is_pooled("postgresql://u:p@ep-x.neon.tech/db")
    assert not is_pooled("postgresql://u:p@localhost/db")


def test_engine_for_pooled_endpoint_disables_statement_caches():
    url = normalize_database_url(NEON)
    engine = build_engine(url, Settings())
    assert engine.url.query["prepared_statement_cache_size"] == "0"
    assert engine.dialect.connect_args if hasattr(engine.dialect, "connect_args") else True
    assert engine.pool.size() == 5 and engine.pool._max_overflow == 5
    assert engine.pool._pre_ping and engine.pool._recycle == 300


def test_engine_for_direct_endpoint_keeps_defaults():
    engine = build_engine("postgresql+asyncpg://u:p@localhost/db", Settings())
    assert "prepared_statement_cache_size" not in engine.url.query


def test_db_pooled_setting_overrides_autodetect():
    forced = build_engine("postgresql+asyncpg://u:p@localhost/db", Settings(db_pooled=True))
    assert forced.url.query["prepared_statement_cache_size"] == "0"
    off = build_engine(
        "postgresql+asyncpg://u:p@ep-x-pooler.neon.tech/db", Settings(db_pooled=False)
    )
    assert "prepared_statement_cache_size" not in off.url.query


async def test_sql_errors_do_not_include_bound_parameters():
    """Con `hide_parameters` el error no lleva `[parameters: ...]` (nombres, direcciones...)."""
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import get_settings

    url = get_settings().database_url_test
    stmt = text("select cast(:x as int)")

    async def message(engine) -> str:
        try:
            async with engine.connect() as conn:
                await conn.execute(stmt, {"x": "valor-secreto-del-cliente"})
        except DBAPIError as e:
            return str(e)
        finally:
            await engine.dispose()
        raise AssertionError("debía fallar")

    assert "[parameters:" in await message(create_async_engine(url))  # sin la protección, se filtra
    assert "[parameters:" not in await message(build_engine(url, Settings()))
