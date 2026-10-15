import hashlib
import hmac
import json
import time

import pytest

from app.core.config import Settings, get_settings
from app.main import app
from tests.conftest import SID

SECRET = {"X-Vapi-Secret": "change-me"}


def use(**kw):
    app.dependency_overrides[get_settings] = lambda: Settings(**kw)


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.dependency_overrides.pop(get_settings, None)


def body():
    call = {"id": "t1", "function": {"name": "get_menu", "arguments": {}}}
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": "c1", "metadata": {"sessionId": SID}},
            "toolCallList": [call],
        }
    }


async def test_capture_is_off_by_default(client, tmp_path):
    use(capture_payloads_dir="")
    await client.post("/vapi/tools", json=body(), headers=SECRET)
    assert list(tmp_path.iterdir()) == []


async def test_vapi_payload_is_saved_without_secrets(client, tmp_path):
    use(capture_payloads_dir=str(tmp_path / "caps"))
    r = await client.post(
        "/vapi/tools", json=body(), headers={**SECRET, "Authorization": "Bearer otro"}
    )
    assert r.status_code == 200
    [file] = list((tmp_path / "caps").iterdir())
    assert file.name.endswith("-vapi-tools.json")
    rec = json.loads(file.read_text())
    assert rec["path"] == "/vapi/tools" and rec["body"] == body()
    assert set(rec["headers"]) <= {"content-type", "user-agent"}
    assert "change-me" not in file.read_text() and "otro" not in file.read_text()


async def test_unauthenticated_requests_are_not_captured(client, tmp_path):
    use(capture_payloads_dir=str(tmp_path))
    assert (await client.post("/vapi/tools", json=body())).status_code == 401
    assert (
        await client.post("/vapi/webhook", json=body(), headers={"X-Vapi-Secret": "mal"})
    ).status_code == 401
    assert list(tmp_path.iterdir()) == []


async def test_retell_payload_is_saved_after_signature_check(client, tmp_path):
    use(capture_payloads_dir=str(tmp_path), retell_api_key="k")
    raw = json.dumps({"event": "call_started", "call": {"call_id": "r1"}})
    ts = str(int(time.time() * 1000))
    sig = f"v={ts},d={hmac.new(b'k', (raw + ts).encode(), hashlib.sha256).hexdigest()}"
    headers = {"Content-Type": "application/json", "X-Retell-Signature": sig}
    assert (await client.post("/retell/webhook", content=raw, headers=headers)).status_code == 200
    [file] = list(tmp_path.iterdir())
    rec = json.loads(file.read_text())
    assert rec["body"]["call"]["call_id"] == "r1" and "x-retell-signature" not in rec["headers"]
    bad = {**headers, "X-Retell-Signature": "v=1,d=" + "0" * 64}
    assert (await client.post("/retell/webhook", content=raw, headers=bad)).status_code == 401
    assert len(list(tmp_path.iterdir())) == 1


async def test_non_json_body_is_stored_as_text(client, tmp_path):
    use(capture_payloads_dir=str(tmp_path))
    await client.post(
        "/vapi/webhook", content="no es json", headers={**SECRET, "Content-Type": "text/plain"}
    )
    [file] = list(tmp_path.iterdir())
    assert json.loads(file.read_text())["body"] == "no es json"
