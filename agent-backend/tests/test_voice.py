import pytest

from app.core.config import Settings, get_settings
from app.main import app


def use(**kw):
    app.dependency_overrides[get_settings] = lambda: Settings(**kw)


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.dependency_overrides.pop(get_settings, None)


async def test_config_follows_voice_provider(client):
    use(voice_provider="retell")
    assert (await client.get("/voice/config")).json() == {"provider": "retell"}
    use(voice_provider="vapi")
    assert (await client.get("/voice/config")).json() == {"provider": "vapi"}


async def test_vapi_web_call_returns_public_config_only(client):
    use(
        voice_provider="vapi",
        vapi_public_key="pk_1",
        vapi_assistant_id="as_1",
        vapi_webhook_secret="s",
    )
    r = await client.post(
        "/voice/web-call", json={"session_id": "sess-12345-abcdef", "language": "es"}
    )
    body = r.json()
    assert r.status_code == 200
    assert body["provider"] == "vapi"
    assert body["public_key"] == "pk_1" and body["assistant_id"] == "as_1"
    assert body["metadata"]["sessionId"] == "sess-12345-abcdef"
    assert "access_token" not in body
    assert "secret" not in str(body).lower()


async def test_web_call_not_configured_is_503(client):
    use(voice_provider="vapi")
    r = await client.post("/voice/web-call", json={"session_id": "sess-12345-abcdef"})
    assert r.status_code == 503


async def test_web_call_validates_input(client):
    use(voice_provider="vapi")
    assert (await client.post("/voice/web-call", json={"session_id": "corto"})).status_code == 422
    bad = {"session_id": "sess con espacios!!"}
    assert (await client.post("/voice/web-call", json=bad)).status_code == 422
    r = await client.post(
        "/voice/web-call", json={"session_id": "sess-12345-abcdef", "language": "fr"}
    )
    assert r.status_code == 422
