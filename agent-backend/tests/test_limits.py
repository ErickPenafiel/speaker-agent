import datetime as dt

import pytest

from app.core import limits
from app.core.config import Settings, get_settings
from app.core.limits import DailyCap, limiter, web_call_cap
from app.main import app
from tests.conftest import SID

HEADERS = {"X-Vapi-Secret": "change-me"}


@pytest.fixture
def limited(monkeypatch):
    """Activa el limitador con límites bajos y los restaura al terminar. Los límites se leen de
    `limits.get_settings` (no de la dependencia de FastAPI), por eso se parchean ambos."""
    settings = Settings(
        vapi_public_key="pk",
        vapi_assistant_id="as",
        rate_limit_panel="3/minute",
        rate_limit_write="1/minute",
        rate_limit_web_call="2/minute",
        web_call_daily_cap=0,
    )
    limiter.enabled = True
    limiter.reset()
    monkeypatch.setattr(limits, "get_settings", lambda: settings)
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


async def test_panel_reads_are_rate_limited_per_ip(client, limited):
    codes = [(await client.get("/orders")).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    r = await client.get("/orders")
    assert r.json()["detail"].startswith("Demasiadas peticiones")
    assert 0 < int(r.headers["Retry-After"]) <= 60


async def test_rate_limit_is_independent_per_route_and_resets(client, limited):
    for _ in range(3):
        await client.get("/orders")
    assert (await client.get("/orders")).status_code == 429
    assert (await client.get("/health")).status_code == 200  # sin límite
    assert (await client.get("/menu")).status_code == 200
    limiter.reset()
    assert (await client.get("/orders")).status_code == 200


async def test_writes_have_their_own_stricter_limit(client, limited):
    missing = "00000000-0000-0000-0000-000000000000"
    codes = [
        (await client.patch(f"/orders/{missing}/status", json={"status": "preparing"})).status_code
        for _ in range(3)
    ]
    assert codes == [404, 429, 429]


async def test_webhooks_and_tools_are_not_rate_limited(client, limited):
    body = {"message": {"type": "tool-calls", "toolCallList": []}}
    codes = {
        (await client.post("/vapi/tools", json=body, headers=HEADERS)).status_code
        for _ in range(10)
    }
    assert codes == {200}


async def test_web_call_is_limited_per_ip(client, limited):
    body = {"session_id": SID, "language": "es"}
    codes = [(await client.post("/voice/web-call", json=body)).status_code for _ in range(4)]
    assert codes == [200, 200, 429, 429]


async def test_web_call_daily_cap_blocks(client):
    app.dependency_overrides[get_settings] = lambda: Settings(
        vapi_public_key="pk", vapi_assistant_id="as", web_call_daily_cap=2
    )
    body = {"session_id": SID}
    try:
        codes = [(await client.post("/voice/web-call", json=body)).status_code for _ in range(3)]
        r = await client.post("/voice/web-call", json=body)
    finally:
        app.dependency_overrides.pop(get_settings, None)
    assert codes == [200, 200, 429]
    assert "límite diario" in r.json()["detail"]


def test_daily_cap_unit():
    cap = DailyCap()
    d1, d2 = dt.date(2026, 10, 8), dt.date(2026, 10, 9)
    assert [cap.hit(2, d1) for _ in range(3)] == [True, True, False]
    assert cap.hit(2, d2) is True  # nuevo día, contador a cero
    assert all(cap.hit(0, d1) for _ in range(100))  # 0 = sin tope
    web_call_cap.reset()
