import asyncio
import datetime as dt

import pytest
from sqlalchemy import func, select, update

from app.core.session import DEMO_SESSION
from app.db.models import Call, Order, OrderItem, Reservation, Transfer
from app.jobs.cleanup import cleanup_loop, purge_old
from app.schemas.call_report import CallReport
from app.services.call_service import save_report
from tests.conftest import SID

OLD = dt.datetime(2026, 9, 1, tzinfo=dt.UTC)


async def total(session, model) -> int:
    return await session.scalar(select(func.count()).select_from(model))


async def populate(session, sid, created):
    from seed.menu import seed_menu

    await seed_menu(session)
    from app.db.models import MenuItem

    item = await session.scalar(select(MenuItem))
    o = Order(session_id=sid, customer_name="x", type="pickup", total=1, created_at=created)
    o.items = [OrderItem(menu_item_id=item.id, name=item.name, unit_price=item.price, quantity=1)]
    session.add_all(
        [
            o,
            Reservation(
                session_id=sid,
                customer_name="x",
                party_size=2,
                date=dt.date(2026, 10, 9),
                time=dt.time(20),
                created_at=created,
            ),
            Transfer(session_id=sid, reason="x", created_at=created),
        ]
    )
    await session.commit()
    c = await save_report(
        session, CallReport("vapi", f"call-{sid}-{created.isoformat()}", session_id=sid)
    )
    await session.execute(update(Call).where(Call.id == c.id).values(created_at=created))
    await session.commit()


async def test_purge_deletes_old_visitor_data_only(session):
    now = dt.datetime(2026, 10, 8, tzinfo=dt.UTC)
    await populate(session, SID, OLD)  # vieja, de un visitante: se borra
    await populate(session, SID, now - dt.timedelta(days=1))  # reciente: se queda
    await populate(session, DEMO_SESSION, OLD)  # demo vieja: se queda
    await populate(session, None, OLD)  # sin sesión (invisible para todos): se borra

    deleted = await purge_old(session, 7, now=now)
    assert deleted == {"orders": 2, "reservations": 2, "transfers": 2, "calls": 2}
    for model in (Order, Reservation, Transfer, Call):
        assert await total(session, model) == 2
    remaining = set(await session.scalars(select(Order.session_id)))
    assert remaining == {SID, DEMO_SESSION}
    assert await total(session, OrderItem) == 2  # las líneas de los borrados cayeron en cascada


async def test_purge_with_nothing_old(session):
    assert await purge_old(session, 7) == {
        "orders": 0,
        "reservations": 0,
        "transfers": 0,
        "calls": 0,
    }


async def test_cleanup_loop_runs_then_sleeps_and_survives_errors(session):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.config import get_settings

    engine = create_async_engine(get_settings().database_url_test)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    await populate(session, SID, OLD)
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await cleanup_loop(factory, interval_hours=6, retention_days=7, sleep=fake_sleep)
    await engine.dispose()
    assert sleeps == [6 * 3600, 6 * 3600]
    assert await total(session, Order) == 0

    # un fallo no mata el bucle
    class Broken:
        def __call__(self):
            raise RuntimeError("db caída")

    sleeps.clear()
    with pytest.raises(asyncio.CancelledError):
        await cleanup_loop(Broken(), interval_hours=1, retention_days=7, sleep=fake_sleep)
    assert sleeps == [3600, 3600]
