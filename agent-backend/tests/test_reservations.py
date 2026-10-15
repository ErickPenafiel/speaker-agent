import asyncio
import datetime as dt

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.errors import BusinessError
from app.db.models import Reservation, Transfer
from app.schemas.reservations import CreateReservationArgs
from app.services import reservation_service as rs
from app.services.reservation_service import create_reservation_tool
from app.services.transfer_service import MESSAGE, transfer_tool
from tests.conftest import SID

HEADERS = {"X-Vapi-Secret": "change-me"}
NOW = dt.datetime(2026, 10, 8, 15, 0)  # jueves 15:00, hora local del restaurante


@pytest.fixture(autouse=True)
def fixed_now(monkeypatch):
    monkeypatch.setattr(rs, "_now", lambda: NOW)


def res(**kw):
    base = {"customer_name": "Ana Pérez", "party_size": 4, "date": "2026-10-09", "time": "20:00"}
    return {**base, **kw}


async def count(session, model=Reservation) -> int:
    return await session.scalar(select(func.count()).select_from(model))


# ---------- reglas de la reserva ----------


async def test_valid_reservation(session):
    text = await create_reservation_tool(session, res(notes="cumpleaños"), tool_call_id="t1")
    await session.commit()
    assert text == "Reserva confirmada para 4 personas mañana a las 20:00 a nombre de Ana Pérez."
    r = await session.scalar(select(Reservation))
    assert (r.date, r.time, r.notes) == (dt.date(2026, 10, 9), dt.time(20, 0), "cumpleaños")


async def test_far_date_is_spoken_with_weekday(session):
    text = await create_reservation_tool(session, res(date="2026-10-16", party_size=1))
    assert "1 persona el viernes 16 de octubre a las 20:00" in text


async def test_party_too_large_suggests_human(session):
    with pytest.raises(BusinessError, match=r"más de 12 personas.*pasar con una persona"):
        await create_reservation_tool(session, res(party_size=20))
    assert await count(session) == 0


@pytest.mark.parametrize(
    ("when", "expected"),
    [
        (
            ("2026-10-09", "09:00"),
            "Atendemos de 12:00 a 23:00; la última reserva es a las 22:00. ¿Le sirve mañana a las 12:00?",
        ),
        (("2026-10-09", "22:30"), "¿Le sirve mañana a las 22:00?"),
        (("2026-10-09", "23:00"), "¿Le sirve mañana a las 22:00?"),
        (("2026-10-08", "03:00"), "Esa hora ya pasó o es muy pronto. ¿Le sirve hoy a las 15:30?"),
        (("2026-10-08", "15:10"), "Esa hora ya pasó o es muy pronto. ¿Le sirve hoy a las 15:30?"),
        (("2026-10-01", "20:00"), "Esa hora ya pasó o es muy pronto. ¿Le sirve hoy a las 15:30?"),
        (("2026-10-08", "09:00"), "Esa hora ya pasó o es muy pronto. ¿Le sirve hoy a las 15:30?"),
    ],
)
async def test_invalid_slots_get_an_alternative(session, when, expected):
    with pytest.raises(BusinessError) as e:
        await create_reservation_tool(session, res(date=when[0], time=when[1]))
    assert expected in str(e.value)
    assert await count(session) == 0


async def test_boundaries_are_accepted(session):
    await create_reservation_tool(session, res(time="12:00"), tool_call_id="a")
    await create_reservation_tool(session, res(time="22:00"), tool_call_id="b")
    await create_reservation_tool(session, res(time="15:30", date="2026-10-08"), tool_call_id="c")
    await create_reservation_tool(session, res(party_size=12), tool_call_id="d")
    assert await count(session) == 4


async def test_late_today_proposes_tomorrow_opening(session, monkeypatch):
    monkeypatch.setattr(rs, "_now", lambda: dt.datetime(2026, 10, 8, 21, 50))
    with pytest.raises(BusinessError, match="¿Le sirve mañana a las 12:00?"):
        await create_reservation_tool(session, res(date="2026-10-08", time="21:00"))


async def test_early_morning_today_proposes_opening(session, monkeypatch):
    monkeypatch.setattr(rs, "_now", lambda: dt.datetime(2026, 10, 8, 8, 10))
    with pytest.raises(BusinessError, match="¿Le sirve hoy a las 12:00?"):
        await create_reservation_tool(session, res(date="2026-10-08", time="08:30"))


async def test_too_far_ahead(session):
    with pytest.raises(BusinessError, match="hasta 60 días"):
        await create_reservation_tool(session, res(date="2027-03-01"))


@pytest.mark.parametrize(
    "bad",
    [{}, res(customer_name=""), res(party_size=0), res(party_size="muchos"), res(date="mañana"),
     res(time="8"), res(time="noche"), res(date=None)],
)  # fmt: skip
async def test_bad_args(session, bad):
    with pytest.raises(BusinessError, match="Me faltan datos de la reserva"):
        await create_reservation_tool(session, bad)


def test_time_formats():
    for raw, want in [("20:00", dt.time(20)), ("20:00:00", dt.time(20)), ("8:00 PM", dt.time(20)),
                      ("8pm", dt.time(20)), ("7:30 p.m.", dt.time(19, 30)), ("12:00 AM", dt.time(0))]:  # fmt: skip
        assert CreateReservationArgs(**res(time=raw)).time == want


# ---------- idempotencia ----------


async def test_same_tool_call_does_not_duplicate(session):
    first = await create_reservation_tool(session, res(), call_id="c", tool_call_id="same")
    await session.commit()
    again = await create_reservation_tool(session, res(), call_id="c", tool_call_id="same")
    assert "confirmada" in first and "ya estaba registrada" in again
    assert await count(session) == 1


async def test_retell_style_dedupe_by_call_and_args(session):
    await create_reservation_tool(session, res(), call_id="call_1")
    await session.commit()
    assert "ya estaba registrada" in await create_reservation_tool(session, res(), call_id="call_1")
    await create_reservation_tool(session, res(time="21:00"), call_id="call_1")
    await session.commit()
    assert await count(session) == 2


async def test_duplicate_wins_even_if_slot_is_now_in_the_past(session, monkeypatch):
    """Un reintento tardío del proveedor debe devolver la reserva existente, no un error."""
    await create_reservation_tool(session, res(), tool_call_id="late")
    await session.commit()
    monkeypatch.setattr(rs, "_now", lambda: dt.datetime(2026, 10, 9, 21, 0))
    assert "ya estaba registrada" in await create_reservation_tool(
        session, res(), tool_call_id="late"
    )


async def test_concurrent_duplicates(session):
    engine = create_async_engine(get_settings().database_url_test)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def attempt():
        async with factory() as s:
            text = await create_reservation_tool(s, res(), call_id="c", tool_call_id="race")
            await s.commit()
            return text

    results = await asyncio.gather(*[attempt() for _ in range(4)])
    await engine.dispose()
    assert await count(session) == 1
    assert sum("confirmada" in r for r in results) == 1


# ---------- transferencia ----------


async def test_transfer_records_and_is_idempotent(session):
    text = await transfer_tool(session, {"reason": "alergia grave"}, call_id="c", tool_call_id="x")
    await session.commit()
    await transfer_tool(session, {"reason": "alergia grave"}, call_id="c", tool_call_id="x")
    await session.commit()
    assert text == MESSAGE
    assert await count(session, Transfer) == 1
    t = await session.scalar(select(Transfer))
    assert t.reason == "alergia grave" and t.call_id == "c"


async def test_transfer_without_reason_uses_default(session):
    await transfer_tool(session, {}, call_id="c2", tool_call_id="y")
    await session.commit()
    assert (await session.scalar(select(Transfer))).reason == "no especificado"


# ---------- por las rutas ----------


def vapi_body(name, args, id_):
    call = {"id": id_, "function": {"name": name, "arguments": args}}
    return {"message": {"type": "tool-calls", "call": {"id": "call_z"}, "toolCallList": [call]}}


async def test_reservation_and_transfer_through_vapi_route(session, client):
    r = await client.post(
        "/vapi/tools", json=vapi_body("create_reservation", res(), "t9"), headers=HEADERS
    )
    assert "Reserva confirmada" in r.json()["results"][0]["result"]
    r = await client.post(
        "/vapi/tools",
        json=vapi_body("transfer_to_human", {"reason": "queja"}, "t10"),
        headers=HEADERS,
    )
    assert r.json()["results"][0]["result"] == MESSAGE
    r = await client.post(
        "/vapi/tools",
        json=vapi_body("create_reservation", res(party_size=30), "t11"),
        headers=HEADERS,
    )
    assert "pasar con una persona" in r.json()["results"][0]["result"]
    assert await count(session) == 1 and await count(session, Transfer) == 1


async def test_list_reservations_sorted_and_filtered(session, client):
    for i, (d, t, n) in enumerate([("2026-10-10", "21:00", "Carla"), ("2026-10-09", "20:00", "Ana"),
                                   ("2026-10-09", "13:00", "Beto")]):  # fmt: skip
        await create_reservation_tool(
            session, res(date=d, time=t, customer_name=n), tool_call_id=f"r{i}", session_id=SID
        )
    await session.commit()

    names = lambda rows: [r["customer_name"] for r in rows]
    got = (await client.get("/reservations")).json()
    assert names(got) == ["Beto", "Ana", "Carla"]  # por fecha y hora
    assert got[0]["time"] == "13:00:00" and got[0]["date"] == "2026-10-09"
    assert names(
        (await client.get("/reservations", params={"date_from": "2026-10-10"})).json()
    ) == ["Carla"]
    assert names((await client.get("/reservations", params={"date_to": "2026-10-09"})).json()) == [
        "Beto",
        "Ana",
    ]
    assert names((await client.get("/reservations", params={"limit": 1, "offset": 1})).json()) == [
        "Ana"
    ]
    assert (await client.get("/reservations", params={"date_from": "ayer"})).status_code == 422
    newest = max(r["created_at"] for r in got)
    assert (await client.get("/reservations", params={"since": newest})).json() == []
