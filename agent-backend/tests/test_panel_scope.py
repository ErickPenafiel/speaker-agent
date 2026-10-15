import datetime as dt

import pytest
from sqlalchemy import func, select

from app.core.session import DEMO_SESSION
from app.db.models import Call, Order, OrderItem, Reservation, Transfer
from app.schemas.call_report import CallReport
from app.services.call_service import save_report
from seed.demo import seed_demo
from tests.conftest import OTHER_SID, SID

NOW = dt.datetime(2026, 10, 8, 18, 0, tzinfo=dt.UTC)
PANELS = ["/orders", "/reservations", "/calls"]


def h(sid):
    return {"X-Session-Id": sid}


async def add_own(session, sid, name="Ana"):
    """Un pedido, una reserva y una llamada de la sesión `sid`."""
    session.add(
        Order(session_id=sid, call_id=f"c-{sid}", customer_name=name, type="pickup", total=10)
    )
    session.add(
        Reservation(
            session_id=sid,
            customer_name=name,
            party_size=2,
            date=dt.date(2026, 10, 9),
            time=dt.time(20),
        )
    )
    await session.commit()
    return await save_report(
        session,
        CallReport(
            "vapi", f"c-{sid}", session_id=sid, transcript=[{"role": "user", "text": "hola"}]
        ),
    )


# ---------- cabecera ----------


@pytest.mark.parametrize("path", PANELS)
async def test_header_is_required_and_validated(client, path):
    no_header = await client.get(path, headers={"X-Session-Id": ""})
    assert no_header.status_code == 422
    for bad in ["corto", "con espacios en el id!!", "x" * 65, DEMO_SESSION]:
        assert (await client.get(path, headers=h(bad))).status_code == 422, bad
    assert (await client.get(path, headers=h("a" * 16))).status_code == 200


async def test_missing_header_entirely(session):
    from httpx import ASGITransport, AsyncClient

    from app.db.session import get_session
    from app.main import app

    async def _s():
        yield session

    app.dependency_overrides[get_session] = _s
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.get("/orders")).status_code == 422
    app.dependency_overrides.clear()


async def test_menu_and_health_do_not_need_a_session(session):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.get("/health")).status_code == 200


# ---------- aislamiento ----------


async def test_visitors_only_see_their_own_data(session, client):
    await add_own(session, SID, "Ana")
    await add_own(session, OTHER_SID, "Beto")
    for path, key in [("/orders", "customer_name"), ("/reservations", "customer_name")]:
        mine = (await client.get(path)).json()
        theirs = (await client.get(path, headers=h(OTHER_SID))).json()
        assert [x[key] for x in mine] == ["Ana"] and [x[key] for x in theirs] == ["Beto"]
        assert not any(x["is_demo"] for x in mine + theirs)
    mine = (await client.get("/calls")).json()
    assert [c["provider_call_id"] for c in mine] == [f"c-{SID}"]


async def test_rows_without_session_are_invisible(session, client):
    session.add(Order(call_id="x", customer_name="Huérfano", type="pickup", total=1))
    await session.commit()
    assert (await client.get("/orders")).json() == []  # nadie los ve, ni siquiera como ejemplo


async def test_cannot_read_or_change_other_visitors_data(session, client):
    await add_own(session, OTHER_SID, "Beto")
    other_order = await session.scalar(select(Order))
    other_call = await session.scalar(select(Call))
    r = await client.patch(f"/orders/{other_order.id}/status", json={"status": "preparing"})
    assert r.status_code == 404
    await session.refresh(other_order)
    assert other_order.status == "confirmed"  # intacto
    assert (await client.get(f"/calls/{other_call.id}")).status_code == 404
    assert (await client.get(f"/calls/{other_call.id}", headers=h(OTHER_SID))).status_code == 200


async def test_own_order_can_be_updated(session, client):
    await add_own(session, SID)
    oid = str(await session.scalar(select(Order.id)))
    r = await client.patch(f"/orders/{oid}/status", json={"status": "preparing"})
    assert (
        r.status_code == 200 and r.json()["status"] == "preparing" and r.json()["is_demo"] is False
    )
    assert "session_id" not in r.json()  # el id de sesión nunca se expone


# ---------- datos de ejemplo ----------


async def test_demo_seed_content(session):
    await seed_demo(session, now=NOW)
    count = lambda m: session.scalar(select(func.count()).select_from(m))
    assert (
        await count(Order),
        await count(Reservation),
        await count(Transfer),
        await count(Call),
    ) == (2, 2, 1, 6)
    outcomes = {c.provider_call_id: c.outcome for c in (await session.scalars(select(Call))).all()}
    assert outcomes == {
        "demo-call-1": "order", "demo-call-2": "order", "demo-call-3": "reservation",
        "demo-call-4": "info", "demo-call-5": "transferred", "demo-call-6": "abandoned",
    }  # fmt: skip
    totals = {o.customer_name: o.total for o in (await session.scalars(select(Order))).all()}
    assert totals == {"Carlos Mendoza": 108, "Lucía Rojas": 95}
    assert await count(OrderItem) == 4


async def test_demo_seed_is_idempotent_and_leaves_visitors_alone(session):
    await add_own(session, SID)
    await seed_demo(session, now=NOW)
    await seed_demo(session, now=NOW)
    n = await session.scalar(
        select(func.count()).select_from(Order).where(Order.session_id == DEMO_SESSION)
    )
    assert n == 2
    assert (
        await session.scalar(select(func.count()).select_from(Order).where(Order.session_id == SID))
        == 1
    )


async def test_empty_visitor_sees_demo_data_flagged(session, client):
    await seed_demo(session, now=NOW)
    orders = (await client.get("/orders")).json()
    assert len(orders) == 2 and all(o["is_demo"] for o in orders)
    assert [o["status"] for o in orders] == ["preparing", "ready"]  # más nuevo primero
    assert len((await client.get("/reservations")).json()) == 2
    calls = (await client.get("/calls")).json()
    assert len(calls) == 6 and all(c["is_demo"] for c in calls)
    detail = (await client.get(f"/calls/{calls[0]['id']}")).json()
    assert detail["is_demo"] and detail["transcript"]


async def test_demo_disappears_per_entity_when_visitor_has_data(session, client):
    await seed_demo(session, now=NOW)
    session.add(Order(session_id=SID, customer_name="Propio", type="pickup", total=5))
    await session.commit()
    orders = (await client.get("/orders")).json()
    assert [o["customer_name"] for o in orders] == ["Propio"] and not orders[0]["is_demo"]
    assert (
        len((await client.get("/reservations")).json()) == 2
    )  # sin reservas propias: sigue el ejemplo
    assert (await client.get("/orders", params={"since": "2999-01-01T00:00:00Z"})).json() == []


async def test_other_visitor_still_sees_demo(session, client):
    await seed_demo(session, now=NOW)
    session.add(Order(session_id=SID, customer_name="Propio", type="pickup", total=5))
    await session.commit()
    assert len((await client.get("/orders", headers=h(OTHER_SID))).json()) == 2


async def test_demo_orders_are_read_only(session, client):
    await seed_demo(session, now=NOW)
    demo_id = (await client.get("/orders")).json()[0]["id"]
    r = await client.patch(f"/orders/{demo_id}/status", json={"status": "ready"})
    assert r.status_code == 403 and "solo lectura" in r.json()["detail"]


async def test_demo_call_detail_links_its_records(session, client):
    await seed_demo(session, now=NOW)
    calls = {c["provider_call_id"]: c for c in (await client.get("/calls")).json()}
    d = (await client.get(f"/calls/{calls['demo-call-1']['id']}")).json()
    assert [o["customer_name"] for o in d["orders"]] == ["Carlos Mendoza"] and d["orders"][0][
        "is_demo"
    ]
    d = (await client.get(f"/calls/{calls['demo-call-5']['id']}")).json()
    assert d["transfers"][0]["reason"].startswith("Reclamo")
