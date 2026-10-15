"""Llamadas completas por proveedor, con payloads de tests/fixtures: tools -> reintentos -> reporte final -> panel."""

import datetime as dt
import hashlib
import hmac
import json
import time

import pytest
from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.db.models import Call, Order, Reservation, Transfer
from app.main import app
from app.services import reservation_service as rs
from app.services.transfer_service import MESSAGE
from seed.menu import seed_menu
from tests.conftest import OTHER_SID, SID
from tests.helpers import load

VAPI = {"X-Vapi-Secret": "change-me"}
KEY = "key_test"
SUBS = {"SESSION": SID, "TOMORROW": "2026-10-09"}


@pytest.fixture(autouse=True)
async def _setup(session, monkeypatch):
    monkeypatch.setattr(rs, "_now", lambda: dt.datetime(2026, 10, 8, 15, 0))
    await seed_menu(session)
    app.dependency_overrides[get_settings] = lambda: Settings(retell_api_key=KEY)
    yield
    app.dependency_overrides.pop(get_settings, None)


async def counts(session) -> tuple[int, int, int, int]:
    n = lambda m: session.scalar(select(func.count()).select_from(m))
    return await n(Order), await n(Reservation), await n(Transfer), await n(Call)


def signed(payload: dict) -> tuple[str, dict]:
    raw = json.dumps(payload)
    ts = str(int(time.time() * 1000))
    digest = hmac.new(KEY.encode(), (raw + ts).encode(), hashlib.sha256).hexdigest()
    return raw, {"Content-Type": "application/json", "X-Retell-Signature": f"v={ts},d={digest}"}


async def retell_post(client, path, payload):
    raw, headers = signed(payload)
    return await client.post(path, content=raw, headers=headers)


# ---------- Vapi ----------


async def test_vapi_full_call(session, client):
    tools = load("vapi_tool_calls.json", **SUBS)
    report = load("vapi_end_of_call_report.json", **SUBS)

    r = await client.post("/vapi/tools", json=tools, headers=VAPI)
    results = {x["toolCallId"]: x["result"] for x in r.json()["results"]}
    # Vapi manda las tools en dos formatos a la vez: se ejecuta cada una UNA vez
    assert len(results) == 3
    assert "Pedido 1 confirmado. Total 108 BOB" in results["toolu_01OrderAAAA"]
    assert (
        results["toolu_01ReservBBBB"]
        == "Reserva confirmada para 4 personas mañana a las 20:00 a nombre de Ana Pérez."
    )
    assert results["toolu_01TransferCCCC"] == MESSAGE
    assert await counts(session) == (1, 1, 1, 0)

    # el proveedor reintenta la petición: nada se duplica
    r = await client.post("/vapi/tools", json=tools, headers=VAPI)
    again = [x["result"] for x in r.json()["results"]]
    assert "ya estaba registrado" in again[0] and "ya estaba registrada" in again[1]
    assert await counts(session) == (1, 1, 1, 0)

    # reporte final (y su reintento)
    for _ in range(2):
        assert (await client.post("/vapi/webhook", json=report, headers=VAPI)).json() == {
            "ok": True
        }
    assert await counts(session) == (1, 1, 1, 1)

    [call] = (await client.get("/calls")).json()
    assert call["outcome"] == "order" and call["provider"] == "vapi"
    assert call["duration_seconds"] == 190 and "gerente" in call["summary"]
    detail = (await client.get(f"/calls/{call['id']}")).json()
    assert [t["role"] for t in detail["transcript"]] == ["assistant", "user", "assistant", "user"]
    assert [o["customer_name"] for o in detail["orders"]] == ["Ana Pérez"]
    assert detail["orders"][0]["items"][1]["notes"] == "sin azúcar"
    assert (
        len(detail["reservations"]) == 1
        and detail["transfers"][0]["reason"] == "quiere hablar con el gerente"
    )
    assert detail["orders"][0]["total"] == "108.00" and detail["orders"][0]["type"] == "pickup"

    # otro visitante no ve nada de esto
    for path in ("/orders", "/reservations", "/calls"):
        assert (await client.get(path, headers={"X-Session-Id": OTHER_SID})).json() == []


# ---------- Retell ----------


async def test_retell_full_call(session, client):
    tool_files = [
        "retell_tool_create_order.json",
        "retell_tool_create_reservation.json",
        "retell_tool_transfer.json",
    ]
    first = []
    for name in tool_files:
        r = await retell_post(client, "/retell/tools", load(name, **SUBS))
        assert r.status_code == 200
        first.append(r.text)
    assert "Pedido 1 confirmado. Total 108 BOB" in first[0]
    assert first[1].startswith("Reserva confirmada para 4 personas mañana a las 20:00")
    assert first[2] == MESSAGE
    assert await counts(session) == (1, 1, 1, 0)

    # Retell no manda id por invocación: el reintento se detecta por llamada + argumentos
    for name in tool_files[:2]:
        r = await retell_post(client, "/retell/tools", load(name, **SUBS))
        assert "ya estaba registrad" in r.text
    assert await counts(session) == (1, 1, 1, 0)

    # call_analyzed puede llegar antes que call_ended; ambos se fusionan, y con reintentos
    for name in [
        "retell_call_analyzed.json",
        "retell_call_ended.json",
        "retell_call_analyzed.json",
    ]:
        assert (await retell_post(client, "/retell/webhook", load(name, **SUBS))).status_code == 200
    assert await counts(session) == (1, 1, 1, 1)

    [call] = (await client.get("/calls")).json()
    assert call["outcome"] == "order" and call["provider"] == "retell"
    assert call["duration_seconds"] == 190 and "gerente" in call["summary"]
    detail = (await client.get(f"/calls/{call['id']}")).json()
    assert [t["role"] for t in detail["transcript"]] == ["assistant", "user", "assistant", "user"]
    assert len(detail["orders"]) == len(detail["reservations"]) == len(detail["transfers"]) == 1


async def test_same_conversation_through_both_providers_stays_separate(session, client):
    """Dos proveedores = dos llamadas distintas aunque el contenido coincida."""
    await client.post(
        "/vapi/webhook", json=load("vapi_end_of_call_report.json", **SUBS), headers=VAPI
    )
    await retell_post(client, "/retell/webhook", load("retell_call_ended.json", **SUBS))
    providers = sorted(c["provider"] for c in (await client.get("/calls")).json())
    assert providers == ["retell", "vapi"]
