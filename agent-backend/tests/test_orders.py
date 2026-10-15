import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.errors import BusinessError
from app.db.models import MenuItem, Order
from app.services.idempotency import idempotency_key
from app.services.order_service import (
    create_order_tool,
    resolve_menu_item,
)
from seed.menu import seed_menu
from tests.conftest import SID

HEADERS = {"X-Vapi-Secret": "change-me"}


def order(items, **kw):
    base = {
        "customer_name": "Ana Pérez",
        "type": "pickup",
        "items": items,
        "customer_confirmed": True,
    }
    return {**base, **kw}


async def count(session) -> int:
    return await session.scalar(select(func.count()).select_from(Order))


@pytest.fixture
async def menu(session):
    await seed_menu(session)
    return list((await session.scalars(select(MenuItem))).all())


# ---------- create_order ----------


async def test_valid_order_computes_total_in_backend(session, menu):
    # El LLM intenta colar un total falso: se ignora (no es un campo de la tool).
    args = order(
        [
            {"name": "Lomo a la parrilla", "quantity": 1},
            {"name": "jugo de maracuya", "quantity": 2},
        ],
        total=1,
    )
    text = await create_order_tool(session, args, call_id="c1", tool_call_id="t1")
    await session.commit()
    o = await session.scalar(select(Order))
    assert o.total == Decimal("108.00")  # 78 + 2*15
    assert o.status == "confirmed" and o.number >= 1
    assert f"Pedido {o.number} confirmado. Total 108 BOB" in text
    assert "20 minutos" in text


async def test_delivery_needs_address_and_has_longer_eta(session, menu):
    with pytest.raises(BusinessError, match="dirección"):
        await create_order_tool(session, order([{"name": "silpancho"}], type="delivery"))
    text = await create_order_tool(
        session,
        order([{"name": "silpancho"}], type="a domicilio", address="Calle 5 #10"),
        tool_call_id="t2",
    )
    assert "40 minutos" in text


async def test_requires_explicit_confirmation(session, menu):
    with pytest.raises(BusinessError, match="confirmación"):
        await create_order_tool(session, order([{"name": "silpancho"}], customer_confirmed=False))
    assert await count(session) == 0


async def test_sold_out_item_creates_nothing(session, menu):
    with pytest.raises(BusinessError, match="Anticuchos está agotado"):
        await create_order_tool(
            session, order([{"name": "silpancho"}, {"name": "Anticuchos"}]), tool_call_id="t3"
        )
    assert await count(session) == 0


async def test_unknown_item_and_bad_args(session, menu):
    with pytest.raises(BusinessError, match="No encontré pizza"):
        await create_order_tool(session, order([{"name": "pizza"}]))
    for bad in [{}, order([]), order([{"name": "x", "quantity": 0}]), order([{"quantity": 2}])]:
        with pytest.raises(BusinessError, match="Me faltan datos"):
            await create_order_tool(session, bad)


async def test_order_by_menu_id_and_string_quantity(session, menu):
    lomo = next(m for m in menu if m.name.startswith("Lomo"))
    await create_order_tool(
        session, order([{"id": str(lomo.id), "quantity": "2"}]), tool_call_id="t4"
    )
    o = await session.scalar(select(Order))
    assert o.total == lomo.price * 2


async def test_same_tool_call_id_does_not_duplicate(session, menu):
    args = order([{"name": "silpancho"}])
    first = await create_order_tool(session, args, call_id="c", tool_call_id="same")
    await session.commit()
    second = await create_order_tool(session, args, call_id="c", tool_call_id="same")
    assert "ya estaba registrado" in second and "confirmado" in first
    assert await count(session) == 1


async def test_retell_style_idempotency_without_tool_call_id(session, menu):
    args = order([{"name": "silpancho"}])
    await create_order_tool(session, args, call_id="call_9")
    await session.commit()
    again = await create_order_tool(session, args, call_id="call_9")
    assert "ya estaba registrado" in again
    assert await count(session) == 1
    # Otro pedido distinto en la misma llamada sí se crea
    await create_order_tool(session, order([{"name": "sopa de mani"}]), call_id="call_9")
    await session.commit()
    assert await count(session) == 2


def test_idempotency_key_rules():
    assert idempotency_key(None, None, {}) is None
    a = idempotency_key("c", None, {"x": 1, "y": 2})
    assert a == idempotency_key("c", None, {"y": 2, "x": 1})  # independiente del orden
    assert a != idempotency_key("c", None, {"x": 2})
    assert len(idempotency_key("c", "tool", {})) <= 64


async def test_concurrent_duplicates_create_one_order(session, menu):
    """Dos peticiones simultáneas con la misma clave: gana una, la otra detecta el duplicado."""
    engine = create_async_engine(get_settings().database_url_test)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    args = order([{"name": "silpancho"}])

    async def attempt():
        async with factory() as s:
            text = await create_order_tool(s, args, call_id="c", tool_call_id="race")
            await s.commit()
            return text

    results = await asyncio.gather(*[attempt() for _ in range(4)])
    await engine.dispose()
    assert await count(session) == 1
    assert sum("confirmado" in r for r in results) == 1
    assert sum("ya estaba registrado" in r for r in results) == 3


# ---------- resolución de platos ----------


async def test_resolve_cases(menu):
    assert resolve_menu_item(menu, item_id=None, name="LOMO").name == "Lomo a la parrilla"
    assert resolve_menu_item(menu, item_id=None, name="un jugo de maracuyá").name.startswith("Jugo")
    assert resolve_menu_item(menu, item_id=None, name="Silpancho ").name == "Silpancho"
    assert resolve_menu_item(menu, item_id=None, name="silpanco").name == "Silpancho"  # errata
    with pytest.raises(BusinessError, match="varias opciones"):
        resolve_menu_item(menu, item_id=None, name="de")  # coincide con varios platos


# ---------- tool por la ruta de Vapi y panel ----------


async def test_create_order_through_vapi_route_then_panel(session, client, menu):
    call = {
        "id": "tc_77",
        "type": "function",
        "function": {
            "name": "create_order",
            "arguments": order([{"name": "pique macho", "quantity": 1}]),
        },
    }
    body = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "call_x", "metadata": {"sessionId": SID}},
            "toolCallList": [call],
        }
    }
    r = await client.post("/vapi/tools", json=body, headers=HEADERS)
    assert "confirmado. Total 85 BOB" in r.json()["results"][0]["result"]
    # reintento de Vapi con el mismo id
    r2 = await client.post("/vapi/tools", json=body, headers=HEADERS)
    assert "ya estaba registrado" in r2.json()["results"][0]["result"]

    r = await client.get("/orders")
    [o] = r.json()
    assert o["customer_name"] == "Ana Pérez" and o["call_id"] == "call_x"
    assert o["items"][0]["name"] == "Pique macho" and o["total"] == "85.00"


# ---------- panel ----------


async def make(client, name):
    body = {
        "message": {
            "type": "tool-calls",
            "call": {"id": f"call_{name}", "metadata": {"sessionId": SID}},
            "toolCallList": [
                {
                    "id": name,
                    "function": {
                        "name": "create_order",
                        "arguments": order([{"name": "silpancho"}], customer_name=name),
                    },
                }
            ],
        }
    }
    await client.post("/vapi/tools", json=body, headers=HEADERS)


async def test_list_orders_paginates_newest_first(client, menu):
    for n in ("Ana", "Beto", "Carla"):
        await make(client, n)
    names = [o["customer_name"] for o in (await client.get("/orders")).json()]
    assert names == ["Carla", "Beto", "Ana"]
    page = (await client.get("/orders", params={"limit": 1, "offset": 1})).json()
    assert [o["customer_name"] for o in page] == ["Beto"]
    assert (await client.get("/orders", params={"limit": 0})).status_code == 422
    newest = (await client.get("/orders")).json()[0]["created_at"]
    assert (await client.get("/orders", params={"since": newest})).json() == []


async def test_status_transitions(client, menu):
    await make(client, "Ana")
    oid = (await client.get("/orders")).json()[0]["id"]

    async def patch(status):
        return await client.patch(f"/orders/{oid}/status", json={"status": status})

    assert (await patch("ready")).status_code == 409  # no se puede saltar
    r = await patch("preparing")
    assert r.status_code == 200 and r.json()["status"] == "preparing"
    assert (await patch("preparing")).status_code == 200  # idempotente
    assert (await patch("ready")).json()["status"] == "ready"
    assert (await patch("confirmed")).status_code == 409  # no se retrocede
    assert (await patch("cocinando")).status_code == 422
    missing = "00000000-0000-0000-0000-000000000000"
    r = await client.patch(f"/orders/{missing}/status", json={"status": "preparing"})
    assert r.status_code == 404
