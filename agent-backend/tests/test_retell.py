import hashlib
import hmac
import json
import time

import httpx
import pytest

from app.core.config import Settings, get_settings
from app.main import app
from app.providers.registry import get_voice_provider
from app.providers.retell import RetellProvider, verify_signature
from seed.menu import seed_menu

KEY = "key_test"


def sign(body: str, key: str = KEY, ts: int | None = None) -> str:
    ts = ts or int(time.time() * 1000)
    d = hmac.new(key.encode(), (body + str(ts)).encode(), hashlib.sha256).hexdigest()
    return f"v={ts},d={d}"


@pytest.fixture(autouse=True)
def retell_settings():
    app.dependency_overrides[get_settings] = lambda: Settings(
        retell_api_key=KEY, retell_agent_id="agent_1", voice_provider="retell"
    )
    yield
    app.dependency_overrides.pop(get_settings, None)


def test_verify_signature_cases():
    body = '{"a":1}'
    assert verify_signature(body, KEY, sign(body))
    assert not verify_signature(body, "otra", sign(body))
    assert not verify_signature(body + " ", KEY, sign(body))  # cuerpo alterado
    assert not verify_signature(body, KEY, sign(body, ts=int(time.time() * 1000) - 6 * 60 * 1000))
    assert not verify_signature(body, KEY, "basura")
    assert not verify_signature(body, "", sign(body, key=""))  # sin clave configurada


async def post_tool(client, payload: dict, signature: str | None = "auto"):
    raw = json.dumps(payload)
    headers = {"Content-Type": "application/json"}
    if signature == "auto":
        headers["X-Retell-Signature"] = sign(raw)
    elif signature:
        headers["X-Retell-Signature"] = signature
    return await client.post("/retell/tools", content=raw, headers=headers)


async def test_tool_requires_valid_signature(client):
    p = {"name": "get_menu", "args": {}}
    assert (await post_tool(client, p, signature=None)).status_code == 401
    assert (await post_tool(client, p, signature="v=1,d=" + "0" * 64)).status_code == 401


async def test_tool_runs_get_menu_and_returns_flat_text(session, client):
    await seed_menu(session)
    p = {"name": "get_menu", "args": {"category": "bebidas"}, "call": {"call_id": "c1"}}
    r = await post_tool(client, p)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "Jugo de maracuyá, 15 BOB" in r.text and "\n" not in r.text


async def test_unknown_tool_is_200(client):
    r = await post_tool(client, {"name": "nope", "args": {}})
    assert r.status_code == 200 and r.text == "Herramienta no disponible."


async def test_web_call_creates_retell_call_server_side(client):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json={"call_id": "rc_1", "access_token": "tok_123"})

    settings = Settings(retell_api_key=KEY, retell_agent_id="agent_1", voice_provider="retell")
    provider = RetellProvider(settings, transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_voice_provider] = lambda: provider
    try:
        r = await client.post(
            "/voice/web-call", json={"session_id": "sess-12345-abcdef", "language": "en"}
        )
    finally:
        app.dependency_overrides.pop(get_voice_provider, None)

    assert r.status_code == 200
    assert r.json()["provider"] == "retell" and r.json()["access_token"] == "tok_123"
    assert "public_key" not in r.json()
    assert seen["auth"] == f"Bearer {KEY}" and seen["url"].endswith("/v3/create-web-call")
    assert seen["body"]["agent_id"] == "agent_1"
    assert seen["body"]["metadata"] == {"sessionId": "sess-12345-abcdef", "language": "en"}


async def test_web_call_provider_error_is_502(client):
    provider = RetellProvider(
        Settings(retell_api_key=KEY, retell_agent_id="a"),
        transport=httpx.MockTransport(lambda r: httpx.Response(500)),
    )
    app.dependency_overrides[get_voice_provider] = lambda: provider
    try:
        r = await client.post("/voice/web-call", json={"session_id": "sess-12345-abcdef"})
    finally:
        app.dependency_overrides.pop(get_voice_provider, None)
    assert r.status_code == 502
