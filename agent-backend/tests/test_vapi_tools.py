import json

import pytest

from app.core.errors import BusinessError
from app.services.tool_registry import TOOLS
from seed.menu import seed_menu

HEADERS = {"X-Vapi-Secret": "change-me"}


def body(*calls, type_="tool-calls", **extra):
    return {
        "message": {"type": type_, "call": {"id": "call_1"}, "toolCallList": list(calls), **extra}
    }


def call(name, args, id_="tc_1", as_string=False):
    arguments = json.dumps(args) if as_string else args
    return {"id": id_, "type": "function", "function": {"name": name, "arguments": arguments}}


async def test_requires_secret(client):
    r = await client.post("/vapi/tools", json=body(call("get_menu", {})))
    assert r.status_code == 401
    r = await client.post("/vapi/tools", json=body(), headers={"X-Vapi-Secret": "wrong"})
    assert r.status_code == 401


@pytest.mark.parametrize(
    "headers", [HEADERS, {"Authorization": "Bearer change-me"}], ids=["x-vapi-secret", "bearer"]
)
async def test_accepts_both_auth_styles(client, headers):
    r = await client.post("/vapi/tools", json=body(), headers=headers)
    assert r.status_code == 200


@pytest.mark.parametrize("as_string", [False, True], ids=["object", "json-string"])
async def test_get_menu_through_route(session, client, as_string):
    await seed_menu(session)
    c = call("get_menu", {"category": "bebidas"}, as_string=as_string)
    r = await client.post("/vapi/tools", json=body(c), headers=HEADERS)
    assert r.status_code == 200
    [res] = r.json()["results"]
    assert res["toolCallId"] == "tc_1"
    assert "Jugo de maracuyá, 15 BOB" in res["result"]
    assert "\n" not in res["result"]


async def test_flat_and_nested_shapes(session, client):
    await seed_menu(session)
    flat = {"id": "tc_f", "name": "get_menu", "parameters": {"category": "postres"}}
    r = await client.post("/vapi/tools", json=body(flat), headers=HEADERS)
    assert "Helado de canela" in r.json()["results"][0]["result"]

    nested = {
        "message": {
            "type": "tool-calls",
            "toolWithToolCallList": [
                {
                    "name": "get_menu",
                    "toolCall": {"id": "tc_n", "parameters": {"category": "postres"}},
                }
            ],
        }
    }
    r = await client.post("/vapi/tools", json=nested, headers=HEADERS)
    [res] = r.json()["results"]
    assert res["toolCallId"] == "tc_n" and "Helado de canela" in res["result"]


async def test_unknown_tool(client):
    r = await client.post("/vapi/tools", json=body(call("nope", {})), headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["results"][0]["result"] == "Herramienta no disponible."


async def test_ignores_other_message_types(client):
    r = await client.post("/vapi/tools", json=body(type_="status-update"), headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == {"results": []}


async def test_multiple_calls_with_business_and_unexpected_errors(client, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("secreto interno")

    async def sold_out(*a, **k):
        raise BusinessError("El lomo\nestá agotado")

    monkeypatch.setitem(TOOLS, "boom", boom)
    monkeypatch.setitem(TOOLS, "sold_out", sold_out)
    r = await client.post(
        "/vapi/tools",
        json=body(call("boom", {}, "a"), call("sold_out", {}, "b"), call("nope", {}, "c")),
        headers=HEADERS,
    )
    assert r.status_code == 200
    got = {x["toolCallId"]: x["result"] for x in r.json()["results"]}
    assert got["a"].startswith("Hubo un problema técnico") and "secreto" not in got["a"]
    assert got["b"] == "El lomo está agotado"
    assert got["c"] == "Herramienta no disponible."
