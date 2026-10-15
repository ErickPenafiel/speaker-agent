"""Datos de ejemplo (sesión "demo") para que el panel no se vea vacío. Idempotente:
borra y recrea todo lo de la sesión demo. Las fechas son relativas a hoy, así que conviene
volver a ejecutarlo de vez en cuando.

    uv run python -m seed.demo
"""

import asyncio
import datetime as dt
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import DEMO_SESSION
from app.db.models import Call, MenuItem, Order, OrderItem, Reservation, Transfer
from app.db.session import SessionLocal
from app.schemas.call_report import CallReport
from app.services.call_service import save_report
from seed.menu import seed_menu

U, A = "user", "assistant"


def turns(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"role": r, "text": t} for r, t in pairs]


async def seed_demo(session: AsyncSession, *, now: dt.datetime | None = None) -> None:
    now = now or dt.datetime.now(dt.UTC)
    await seed_menu(session)
    for model in (Order, Reservation, Transfer, Call):
        await session.execute(delete(model).where(model.session_id == DEMO_SESSION))
    menu = {m.name: m for m in (await session.scalars(select(MenuItem))).all()}
    today = now.date()

    def order(call_id, name, kind, status, minutes_ago, lines, address=None):
        items = [
            OrderItem(menu_item_id=menu[n].id, name=n, unit_price=menu[n].price, quantity=q)
            for n, q in lines
        ]
        return Order(
            session_id=DEMO_SESSION, call_id=call_id, customer_name=name, type=kind,
            address=address, status=status, total=sum((i.unit_price * i.quantity for i in items), Decimal(0)),
            created_at=now - dt.timedelta(minutes=minutes_ago), items=items,
        )  # fmt: skip

    session.add_all(
        [
            order("demo-call-1", "Carlos Mendoza", "pickup", "ready", 50,
                  [("Lomo a la parrilla", 1), ("Jugo de maracuyá", 2)]),
            order("demo-call-2", "Lucía Rojas", "delivery", "preparing", 20,
                  [("Pique macho", 1), ("Gaseosa", 1)], address="Av. Arce 1234"),
            Reservation(session_id=DEMO_SESSION, call_id="demo-call-3", customer_name="Familia Vargas",
                        party_size=4, date=today + dt.timedelta(days=1), time=dt.time(20, 0),
                        created_at=now - dt.timedelta(minutes=35)),
            Reservation(session_id=DEMO_SESSION, customer_name="Marcos Salazar", party_size=2,
                        date=today + dt.timedelta(days=2), time=dt.time(13, 30), notes="Cumpleaños",
                        created_at=now - dt.timedelta(hours=3)),
            Transfer(session_id=DEMO_SESSION, call_id="demo-call-5", reason="Reclamo por un pedido anterior",
                     created_at=now - dt.timedelta(minutes=10)),
        ]
    )  # fmt: skip
    await session.commit()

    calls = [
        ("demo-call-1", 50, 95, "Pedido de lomo y dos jugos para recoger.", turns(
            (A, "Las Flamas, habla Sofía. ¿En qué puedo ayudarle?"),
            (U, "Quiero un lomo y dos jugos de maracuyá para recoger."),
            (A, "Un lomo a la parrilla y dos jugos de maracuyá, 108 bolivianos. ¿Confirmo el pedido?"),
            (U, "Sí, a nombre de Carlos Mendoza."),
            (A, "Listo, pedido confirmado. Estará listo en unos 20 minutos."))),
        ("demo-call-2", 20, 120, "Pedido a domicilio de pique macho y gaseosa.", turns(
            (A, "Las Flamas, habla Sofía. ¿En qué puedo ayudarle?"),
            (U, "Un pique macho y una gaseosa, a domicilio."),
            (A, "¿Cuál es la dirección?"),
            (U, "Avenida Arce 1234. Soy Lucía Rojas."),
            (A, "Pedido confirmado, llegará en unos 40 minutos."))),
        ("demo-call-3", 35, 75, "Reserva para 4 personas mañana a las 20:00.", turns(
            (A, "Las Flamas, habla Sofía. ¿En qué puedo ayudarle?"),
            (U, "Quiero reservar para cuatro mañana a las ocho de la noche."),
            (A, "Reserva confirmada para 4 personas mañana a las 20:00 a nombre de Familia Vargas."))),
        ("demo-call-4", 90, 40, "Consulta de horarios y alérgenos.", turns(
            (A, "Las Flamas, habla Sofía. ¿En qué puedo ayudarle?"),
            (U, "¿Hasta qué hora atienden? ¿La sopa de maní tiene gluten?"),
            (A, "Atendemos de 12:00 a 23:00. La sopa de maní contiene maní, no gluten."))),
        ("demo-call-5", 10, 55, "Reclamo; se transfirió a una persona.", turns(
            (A, "Las Flamas, habla Sofía. ¿En qué puedo ayudarle?"),
            (U, "Quiero hablar con alguien, tuve un problema con mi pedido de ayer."),
            (A, "Entiendo, lo comunico con una persona del restaurante."))),
        ("demo-call-6", 150, 6, "Llamada sin interacción del cliente.", turns(
            (A, "Las Flamas, habla Sofía. ¿En qué puedo ayudarle?"))),
    ]  # fmt: skip
    for call_id, minutes_ago, seconds, summary, transcript in calls:
        await save_report(
            session,
            CallReport(
                provider="vapi", provider_call_id=call_id, session_id=DEMO_SESSION,
                started_at=now - dt.timedelta(minutes=minutes_ago), duration_seconds=seconds,
                transcript=transcript, summary=summary,
            ),
        )  # fmt: skip


async def main() -> None:
    async with SessionLocal() as session:
        await seed_demo(session)
    print("Datos de ejemplo creados (sesión demo)")


if __name__ == "__main__":
    asyncio.run(main())
