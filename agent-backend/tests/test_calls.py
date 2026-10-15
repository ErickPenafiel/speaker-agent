import asyncio
import datetime as dt
import hashlib
import hmac
import json
import time

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.db.models import Call, Order, Reservation, Transfer
from app.main import app
from app.providers.retell import parse_call_event
from app.providers.vapi import parse_end_of_call
from app.schemas.call_report import CallReport
from app.services.call_service import derive_outcome, save_report
from tests.conftest import SID

VAPI = {"X-Vapi-Secret": "change-me"}
KEY = "key_test"
USER = {"role": "user", "text": "hola"}
BOT = {"role": "assistant", "text": "Hola, soy Sofía"}


# ---------- payloads ----------


def vapi_report(call_id="call_v1", **over):
    msg = {
        "type": "end-of-call-report",
        "endedReason": "customer-ended-call",
        "call": {"id": call_id, "metadata": {"sessionId": SID}},
        "startedAt": "2026-10-08T15:00:00.000Z",
        "endedAt": "2026-10-08T15:02:30.000Z",
        "analysis": {"summary": "El cliente pidió un lomo."},
        "artifact": {
            "transcript": "AI: Hola User: Hola",
            "messages": [
                {"role": "system", "message": "prompt interno"},
                {"role": "assistant", "message": "Hola, soy Sofía"},
                {"role": "user", "message": "Quiero un lomo"},
                {"role": "tool", "message": "{...}"},
                {"role": "bot", "message": "   "},
            ],
        },
    }
    msg.update(over)
    return {"message": msg}


def retell_payload(event="call_ended", call_id="call_r1", **call_over):
    call = {
        "call_id": call_id,
        "call_status": "ended",
        "metadata": {"sessionId": "sess-bbbb2222"},
        "start_timestamp": 1714608475945,
        "end_timestamp": 1714608491736,
        "transcript_object": [
            {"role": "agent", "content": "Hola, soy Sofía", "words": []},
            {"role": "user", "content": "Quiero reservar", "words": []},
            {"role": "transfer_target", "content": "ignorado"},
        ],
    }
    if event == "call_analyzed":
        call["call_analysis"] = {"call_summary": "Reserva para 4."}
    call.update(call_over)
    return {"event": event, "call": call}


def sign(body: str, ts: int | None = None) -> str:
    ts = ts or int(time.time() * 1000)
    return (
        f"v={ts},d={hmac.new(KEY.encode(), (body + str(ts)).encode(), hashlib.sha256).hexdigest()}"
    )


async def post_retell(client, payload, signature="auto"):
    raw = json.dumps(payload)
    headers = {"Content-Type": "application/json"}
    if signature == "auto":
        headers["X-Retell-Signature"] = sign(raw)
    elif signature:
        headers["X-Retell-Signature"] = signature
    return await client.post("/retell/webhook", content=raw, headers=headers)


@pytest.fixture
def retell_settings():
    app.dependency_overrides[get_settings] = lambda: Settings(retell_api_key=KEY)
    yield
    app.dependency_overrides.pop(get_settings, None)


async def calls(session) -> list[Call]:
    return list((await session.scalars(select(Call))).all())


# ---------- parsers ----------


def test_parse_vapi_full_report():
    r = parse_end_of_call(vapi_report()["message"])
    assert (r.provider, r.provider_call_id, r.session_id) == ("vapi", "call_v1", SID)
    assert r.duration_seconds == 150  # endedAt - startedAt
    assert r.started_at == dt.datetime(2026, 10, 8, 15, 0, tzinfo=dt.UTC)
    assert r.summary == "El cliente pidió un lomo."
    assert r.transcript == [
        {"role": "assistant", "text": "Hola, soy Sofía"},
        {"role": "user", "text": "Quiero un lomo"},
    ]  # sin system/tool/vacíos; "bot" -> assistant (vacío descartado)


def test_parse_vapi_tolerates_alternative_locations():
    msg = vapi_report()["message"]
    msg.pop("analysis")
    msg.update(summary="Resumen plano", durationSeconds=41.6)
    msg["artifact"]["messages"] = [{"role": "user", "content": "texto en content"}]
    r = parse_end_of_call(msg)
    assert r.summary == "Resumen plano" and r.duration_seconds == 42
    assert r.transcript == [{"role": "user", "text": "texto en content"}]


def test_parse_vapi_ignores_other_types_and_missing_id():
    assert parse_end_of_call({"type": "status-update", "call": {"id": "x"}}) is None
    assert parse_end_of_call({"type": "end-of-call-report", "call": {}}) is None


def test_parse_vapi_missing_optional_fields_are_none():
    r = parse_end_of_call({"type": "end-of-call-report", "call": {"id": "c"}})
    assert (r.transcript, r.summary, r.duration_seconds, r.started_at, r.session_id) == (None,) * 5


def test_parse_retell_events():
    ended = parse_call_event(retell_payload("call_ended"))
    assert ended.provider == "retell" and ended.session_id == "sess-bbbb2222"
    assert ended.duration_seconds == 16  # 15 791 ms
    assert ended.started_at == dt.datetime.fromtimestamp(1714608475.945, dt.UTC)
    assert ended.summary is None  # call_ended no trae call_analysis
    assert ended.transcript == [
        {"role": "assistant", "text": "Hola, soy Sofía"},
        {"role": "user", "text": "Quiero reservar"},
    ]
    analyzed = parse_call_event(retell_payload("call_analyzed"))
    assert analyzed.summary == "Reserva para 4."
    assert parse_call_event(retell_payload("call_started")) is None
    assert parse_call_event({"event": "call_ended", "call": {}}) is None


def test_retell_duration_ms_wins_over_timestamps():
    r = parse_call_event(retell_payload(duration_ms=5400))
    assert r.duration_seconds == 5


# ---------- outcome ----------


@pytest.mark.parametrize(
    ("transcript", "o", "r", "t", "want"),
    [
        ([USER, BOT], 1, 1, 1, "order"),
        ([USER], 0, 2, 1, "reservation"),
        ([USER], 0, 0, 1, "transferred"),
        ([BOT, USER], 0, 0, 0, "info"),
        ([BOT], 0, 0, 0, "abandoned"),  # el cliente nunca habló
        ([], 0, 0, 0, "abandoned"),
        (None, 0, 0, 0, "abandoned"),
        (None, 1, 0, 0, "order"),  # aunque falte la transcripción, lo guardado manda
    ],
)
def test_derive_outcome(transcript, o, r, t, want):
    assert derive_outcome(transcript, orders=o, reservations=r, transfers=t) == want


# ---------- save_report ----------


async def seed_records(
    session, call_id, *, order=False, reservation=False, transfer=False, sid=SID
):
    if order:
        session.add(
            Order(call_id=call_id, session_id=sid, customer_name="Ana", type="pickup", total=10)
        )
    if reservation:
        session.add(
            Reservation(
                call_id=call_id,
                session_id=sid,
                customer_name="Ana",
                party_size=2,
                date=dt.date(2026, 10, 9),
                time=dt.time(20),
            )
        )
    if transfer:
        session.add(Transfer(call_id=call_id, session_id=sid, reason="queja"))
    await session.commit()


async def test_save_report_derives_outcome_from_linked_records(session):
    await seed_records(session, "call_v1", order=True, reservation=True)
    call = await save_report(session, parse_end_of_call(vapi_report()["message"]))
    assert call.outcome == "order" and call.provider == "vapi"
    assert call.duration_seconds == 150 and call.summary == "El cliente pidió un lomo."


async def test_save_report_is_idempotent(session):
    report = parse_end_of_call(vapi_report()["message"])
    a = await save_report(session, report)
    b = await save_report(session, report)
    assert a.id == b.id and len(await calls(session)) == 1


async def test_same_id_different_provider_are_different_calls(session):
    await save_report(session, CallReport("vapi", "same", transcript=[USER]))
    await save_report(session, CallReport("retell", "same", transcript=[USER]))
    assert len(await calls(session)) == 2


@pytest.mark.parametrize(
    "order", [("call_ended", "call_analyzed"), ("call_analyzed", "call_ended")]
)
async def test_retell_events_merge_in_any_order(session, order):
    for ev in order:
        await save_report(session, parse_call_event(retell_payload(ev)))
    [c] = await calls(session)
    assert c.summary == "Reserva para 4."  # viene solo en call_analyzed
    assert c.duration_seconds == 16 and len(c.transcript) == 2  # no se pierden por el otro evento
    assert c.outcome == "info"


async def test_null_fields_do_not_overwrite_and_are_sql_null(session):
    await save_report(session, parse_end_of_call(vapi_report()["message"]))
    await save_report(session, CallReport("vapi", "call_v1"))  # evento vacío
    [c] = await calls(session)
    assert c.summary and c.transcript and c.duration_seconds == 150
    # y un reporte sin transcripción guarda NULL de SQL, no JSON null
    await save_report(session, CallReport("vapi", "call_new"))
    n = await session.scalar(
        select(func.count()).select_from(Call).where(Call.transcript.is_(None))
    )
    assert n == 1


async def test_session_id_falls_back_to_linked_records(session):
    await seed_records(session, "call_x", order=True, sid="sess-from-order")
    call = await save_report(session, CallReport("vapi", "call_x", transcript=[USER]))
    assert call.session_id == "sess-from-order"
    # si la llamada trae su propia metadata, esa manda
    await seed_records(session, "call_y", order=True, sid="sess-from-order")
    call = await save_report(
        session, CallReport("vapi", "call_y", session_id="sess-own", transcript=[USER])
    )
    assert call.session_id == "sess-own"


async def test_concurrent_reports_create_one_row(session):
    engine = create_async_engine(get_settings().database_url_test)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    report = parse_end_of_call(vapi_report()["message"])

    async def attempt():
        async with factory() as s:
            await save_report(s, report)

    await asyncio.gather(*[attempt() for _ in range(5)])
    await engine.dispose()
    assert len(await calls(session)) == 1


# ---------- webhooks ----------


async def test_vapi_webhook_requires_secret_and_saves(session, client):
    assert (await client.post("/vapi/webhook", json=vapi_report())).status_code == 401
    r = await client.post("/vapi/webhook", json=vapi_report(), headers=VAPI)
    assert r.status_code == 200 and r.json() == {"ok": True}
    r = await client.post("/vapi/webhook", json=vapi_report(), headers=VAPI)  # reintento
    assert len(await calls(session)) == 1


async def test_vapi_webhook_ignores_other_messages(session, client):
    body = {"message": {"type": "status-update", "status": "in-progress", "call": {"id": "c"}}}
    assert (await client.post("/vapi/webhook", json=body, headers=VAPI)).status_code == 200
    assert await calls(session) == []


async def test_retell_webhook_signature_and_events(session, client, retell_settings):
    p = retell_payload("call_ended")
    assert (await post_retell(client, p, signature=None)).status_code == 401
    assert (await post_retell(client, p, signature="v=1,d=" + "0" * 64)).status_code == 401
    assert await calls(session) == []

    assert (await post_retell(client, p)).status_code == 200
    assert (await post_retell(client, retell_payload("call_analyzed"))).status_code == 200
    assert (
        await post_retell(client, retell_payload("call_started", call_id="other"))
    ).status_code == 200
    [c] = await calls(session)
    assert c.provider == "retell" and c.summary == "Reserva para 4."


# ---------- panel ----------


async def test_list_calls_order_filter_pagination(session, client):
    reports = [
        CallReport(
            "vapi",
            "old",
            session_id=SID,
            started_at=dt.datetime(2026, 10, 1, tzinfo=dt.UTC),
            transcript=[USER],
        ),
        CallReport(
            "vapi",
            "new",
            session_id=SID,
            started_at=dt.datetime(2026, 10, 8, tzinfo=dt.UTC),
            transcript=[BOT],
        ),
        CallReport(
            "retell",
            "mid",
            session_id=SID,
            started_at=dt.datetime(2026, 10, 5, tzinfo=dt.UTC),
            transcript=[USER],
        ),
    ]
    for r in reports:
        await save_report(session, r)

    ids = lambda rows: [r["provider_call_id"] for r in rows]
    got = (await client.get("/calls")).json()
    assert ids(got) == ["new", "mid", "old"]  # más reciente primero
    assert "transcript" not in got[0]  # la lista es liviana
    assert ids((await client.get("/calls", params={"outcome": "abandoned"})).json()) == ["new"]
    assert ids((await client.get("/calls", params={"limit": 1, "offset": 1})).json()) == ["mid"]
    assert (await client.get("/calls", params={"outcome": "otro"})).status_code == 422
    newest = max(r["created_at"] for r in got)
    assert (await client.get("/calls", params={"since": newest})).json() == []


async def test_call_detail_links_records_and_transcript(session, client):
    await seed_records(session, "call_v1", order=True, reservation=True, transfer=True)
    session.add(Order(call_id="otra_llamada", customer_name="Zed", type="pickup", total=1))
    await session.commit()
    await save_report(session, parse_end_of_call(vapi_report()["message"]))
    listed = (await client.get("/calls")).json()
    r = await client.get(f"/calls/{listed[0]['id']}")
    d = r.json()
    assert r.status_code == 200
    assert d["outcome"] == "order" and d["provider"] == "vapi"
    assert [t["role"] for t in d["transcript"]] == ["assistant", "user"]
    assert [o["customer_name"] for o in d["orders"]] == ["Ana"]  # la de otra llamada no aparece
    assert d["orders"][0]["items"] == []
    assert len(d["reservations"]) == 1 and d["transfers"][0]["reason"] == "queja"


async def test_call_detail_without_transcript_and_errors(session, client):
    c = await save_report(session, CallReport("vapi", "bare", session_id=SID))
    d = (await client.get(f"/calls/{c.id}")).json()
    assert d["transcript"] == [] and d["outcome"] == "abandoned"
    assert (await client.get("/calls/00000000-0000-0000-0000-000000000000")).status_code == 404
    assert (await client.get("/calls/no-es-uuid")).status_code == 422


async def test_e2e_tools_then_webhook(session, client):
    """Flujo real: durante la llamada se crea un pedido; al final llega el reporte y lo enlaza."""
    from seed.menu import seed_menu

    await seed_menu(session)
    args = {"customer_name": "Ana Pérez", "type": "pickup", "customer_confirmed": True,
            "items": [{"name": "silpancho"}]}  # fmt: skip
    tool = {"id": "tc1", "function": {"name": "create_order", "arguments": args}}
    body = {"message": {"type": "tool-calls", "call": {"id": "call_v1", "metadata": {"sessionId": SID}},
                        "toolCallList": [tool]}}  # fmt: skip
    await client.post("/vapi/tools", json=body, headers=VAPI)
    await client.post("/vapi/webhook", json=vapi_report("call_v1"), headers=VAPI)

    [c] = (await client.get("/calls")).json()
    assert c["outcome"] == "order"
    d = (await client.get(f"/calls/{c['id']}")).json()
    assert d["orders"][0]["total"] == "48.00"  # enlazado por call_id
