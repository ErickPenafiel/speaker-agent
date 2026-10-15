import json
import logging

import pytest
import structlog

from app.core import observability
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.observability import OMITTED, init_sentry, scrub_event
from app.db.session import get_session
from app.main import app
from app.services import tool_runner
from app.services.tool_registry import TOOLS
from seed.menu import seed_menu
from tests.conftest import SID

VAPI = {"X-Vapi-Secret": "change-me"}


@pytest.fixture
def logs(capsys):
    """Logging JSON real (como en producción); restaura el estado global al terminar."""
    root = logging.getLogger()
    saved = (root.handlers[:], root.level, logging.getLogger("uvicorn.access").disabled)

    def start(level="INFO"):
        configure_logging(level, "json")

    def read() -> list[dict]:
        return [
            json.loads(line)
            for line in capsys.readouterr().err.splitlines()
            if line.startswith("{")
        ]

    start()
    yield type("Logs", (), {"start": staticmethod(start), "read": staticmethod(read)})
    root.handlers, root.level = saved[0], saved[1]
    logging.getLogger("uvicorn.access").disabled = saved[2]
    structlog.reset_defaults()


def vapi_body(name, args, id_="tc1", call_id="call_obs"):
    call = {"id": id_, "function": {"name": name, "arguments": args}}
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": call_id, "metadata": {"sessionId": SID}},
            "toolCallList": [call],
        }
    }


ORDER = {
    "customer_name": "Ana Secreta",
    "type": "pickup",
    "customer_confirmed": True,
    "items": [{"name": "lomo"}],
}


# ---------- formato ----------


def test_json_format_for_structlog_and_stdlib(logs):
    structlog.get_logger("demo").info("hola", numero=1)
    logging.getLogger("uvicorn.error").info("arranque")
    try:
        1 / 0  # noqa: B018
    except ZeroDivisionError:
        structlog.get_logger("demo").exception("fallo")
    a, b, c = logs.read()
    assert (a["event"], a["numero"], a["level"], a["logger"]) == ("hola", 1, "info", "demo")
    assert a["timestamp"].endswith("Z")
    assert b["event"] == "arranque" and b["logger"] == "uvicorn.error"
    assert "ZeroDivisionError" in c["exception"] and c["level"] == "error"


def test_uvicorn_access_log_is_off_because_it_includes_the_query_string(logs):
    logging.getLogger("uvicorn.access").info('127.0.0.1 - "GET /orders?token=secreto HTTP/1.1" 200')
    assert logs.read() == []


# ---------- peticiones ----------


async def test_request_log_has_no_sensitive_data(client, capsys, logs):
    r = await client.get("/orders", params={"since": "2026-01-01T00:00:00Z"})
    # solo lo que emite la aplicación (el cliente de pruebas, httpx, registra su propia petición)
    err = "\n".join(x for x in capsys.readouterr().err.splitlines() if '"logger": "httpx"' not in x)
    [req] = [json.loads(x) for x in err.splitlines() if '"event": "request"' in x]
    assert (req["method"], req["path"], req["status"]) == ("GET", "/orders", 200)
    assert isinstance(req["duration_ms"], int)
    assert req["request_id"] == r.headers["X-Request-Id"]
    for secret in (SID, "since", "2026-01-01"):
        assert secret not in err


async def test_request_id_is_generated_not_taken_from_client(client, logs):
    r = await client.get("/menu", headers={"X-Request-Id": "evil\\nfake-log-line"})
    rid = r.headers["X-Request-Id"]
    assert len(rid) == 12 and all(c in "0123456789abcdef" for c in rid)
    assert (await client.get("/menu")).headers["X-Request-Id"] != rid


async def test_health_checks_are_logged_only_at_debug(client, logs):
    await client.get("/health")
    assert [x for x in logs.read() if x["event"] == "request"] == []
    logs.start("DEBUG")
    await client.get("/health")
    [req] = [x for x in logs.read() if x["event"] == "request"]
    assert req["level"] == "debug" and req["path"] == "/health"


async def test_errors_are_logged_with_their_status(client, logs):
    await client.post("/vapi/tools", json={})
    [req] = [x for x in logs.read() if x["event"] == "request"]
    assert req["status"] == 401


# ---------- tools ----------


async def test_tool_call_log_has_context_but_no_customer_data(session, client, capsys, logs):
    await seed_menu(session)
    r = await client.post("/vapi/tools", json=vapi_body("create_order", ORDER), headers=VAPI)
    err = capsys.readouterr().err
    [tool] = [json.loads(x) for x in err.splitlines() if '"event": "tool_call"' in x]
    assert (tool["tool"], tool["call_id"], tool["outcome"], tool["level"]) == (
        "create_order",
        "call_obs",
        "ok",
        "info",
    )
    assert tool["request_id"] == r.headers["X-Request-Id"] and tool["slow"] is False
    for private in ("Ana", "Secreta", "lomo", "Pedido", "confirmado"):
        assert private not in err, private


async def test_tool_outcomes_are_logged_without_messages(session, client, capsys, logs):
    await seed_menu(session)
    sold_out = {**ORDER, "items": [{"name": "Anticuchos"}]}
    await client.post("/vapi/tools", json=vapi_body("create_order", sold_out, "a"), headers=VAPI)
    await client.post("/vapi/tools", json=vapi_body("no_existe", {}, "b"), headers=VAPI)
    err = capsys.readouterr().err
    outcomes = [json.loads(x)["outcome"] for x in err.splitlines() if '"event": "tool_call"' in x]
    assert outcomes == ["business_error", "unknown_tool"]
    assert "Anticuchos" not in err and "agotado" not in err


async def test_unexpected_tool_error_is_logged_with_traceback_and_warning(
    client, monkeypatch, logs
):
    async def boom(*a, **k):
        raise RuntimeError("falla interna")

    monkeypatch.setitem(TOOLS, "boom", boom)
    await client.post(
        "/vapi/tools", json=vapi_body("boom", {"customer_name": "Ana Secreta"}), headers=VAPI
    )
    lines = logs.read()
    failed = next(x for x in lines if x["event"] == "tool_failed")
    assert "RuntimeError" in failed["exception"] and failed["level"] == "error"
    assert "Ana Secreta" not in json.dumps(lines)
    tool = next(x for x in lines if x["event"] == "tool_call")
    assert tool["outcome"] == "tech_error" and tool["level"] == "warning"


async def test_slow_tools_are_flagged(session, client, monkeypatch, logs):
    await seed_menu(session)
    monkeypatch.setattr(tool_runner, "SLOW_MS", -1)
    await client.post("/vapi/tools", json=vapi_body("get_menu", {}), headers=VAPI)
    tool = next(x for x in logs.read() if x["event"] == "tool_call")
    assert tool["slow"] is True and tool["level"] == "warning"


async def test_call_report_saved_log(client, capsys, logs):
    report = {
        "message": {
            "type": "end-of-call-report",
            "call": {"id": "call_obs", "metadata": {"sessionId": SID}},
            "analysis": {"summary": "Resumen con datos de Ana Secreta"},
            "artifact": {"messages": [{"role": "user", "message": "Me llamo Ana Secreta"}]},
        }
    }
    await client.post("/vapi/webhook", json=report, headers=VAPI)
    err = capsys.readouterr().err
    [saved] = [json.loads(x) for x in err.splitlines() if '"event": "call_report_saved"' in x]
    assert (saved["provider"], saved["call_id"], saved["outcome"], saved["has_transcript"]) == (
        "vapi",
        "call_obs",
        "info",
        True,
    )
    assert "Secreta" not in err


# ---------- Sentry ----------


def test_scrub_event_removes_identifying_data():
    event = {
        "request": {
            "url": "http://api/orders",
            "method": "GET",
            "headers": {"X-Session-Id": SID, "X-Vapi-Secret": "s"},
            "data": {"customer_name": "Ana"},
            "cookies": {"a": "b"},
            "query_string": "since=1",
            "env": {"REMOTE_ADDR": "1.2.3.4"},
        },
        "user": {"ip_address": "1.2.3.4"},
    }
    out = scrub_event(event, {})
    assert out["request"] == {"url": "http://api/orders", "method": "GET"}
    assert "user" not in out


def test_scrub_event_hides_database_error_text_only():
    event = {
        "exception": {
            "values": [
                {
                    "type": "IntegrityError",
                    "module": "sqlalchemy.exc",
                    "value": "DETAIL: Failing row contains (Ana, ...)",
                },
                {"type": "Error", "module": "asyncpg.exceptions", "value": "duplicate key (Ana)"},
                {"type": "RuntimeError", "module": "builtins", "value": "falla interna"},
            ]
        }
    }
    values = scrub_event(event, {})["exception"]["values"]
    assert [v["value"] for v in values] == [OMITTED, OMITTED, "falla interna"]


def test_sentry_is_off_without_dsn(monkeypatch):
    called = []
    monkeypatch.setattr(observability.sentry_sdk, "init", lambda **kw: called.append(kw))
    assert init_sentry(Settings(sentry_dsn="")) is False and called == []


def test_sentry_init_is_privacy_safe(monkeypatch):
    called = []
    monkeypatch.setattr(observability.sentry_sdk, "init", lambda **kw: called.append(kw))
    assert (
        init_sentry(
            Settings(
                sentry_dsn="https://k@o0.ingest.sentry.io/1",
                environment="production",
                release="abc123",
            )
        )
        is True
    )
    [kw] = called
    assert kw["send_default_pii"] is False and kw["max_request_body_size"] == "never"
    assert kw["before_send"] is scrub_event and kw["environment"] == "production"
    assert kw["release"] == "abc123" and kw["traces_sample_rate"] == 0.0


# ---------- readiness ----------


async def test_ready_checks_the_database(client):
    r = await client.get("/health/ready")
    assert r.status_code == 200 and r.json() == {"status": "ok", "db": "ok"}


async def test_ready_returns_503_without_leaking_details(client, logs):
    class Broken:
        async def execute(self, *a, **k):
            raise ConnectionError("password authentication failed for user postgres@10.0.0.5")

    async def broken_session():
        yield Broken()

    app.dependency_overrides[get_session] = broken_session
    r = await client.get("/health/ready")
    assert r.status_code == 503 and r.json() == {"detail": "Base de datos no disponible"}
    assert "10.0.0.5" not in r.text
    assert (await client.get("/health")).status_code == 200  # liveness no depende de la base
    assert any(x["event"] == "readiness_failed" for x in logs.read())


def test_settings_defaults_are_safe():
    s = get_settings.__wrapped__()
    assert s.capture_payloads_dir == "" and s.sentry_dsn == "" and s.environment == "development"
