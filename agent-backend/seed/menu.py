"""Menú ficticio de Las Flamas. Idempotente: `python -m seed.menu`."""

import asyncio
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MenuItem
from app.db.session import SessionLocal

# (nombre, categoría, descripción, precio, alérgenos, disponible)
MENU: list[tuple[str, str, str, str, list[str], bool]] = [
    (
        "Lomo a la parrilla",
        "parrilla",
        "Lomo de res con arroz, papas y ensalada",
        "78.00",
        [],
        True,
    ),
    (
        "Pique macho",
        "parrilla",
        "Carne, salchicha, papas, huevo y locoto",
        "85.00",
        ["huevo"],
        True,
    ),
    ("Costillas BBQ", "parrilla", "Costillas de cerdo en salsa barbacoa", "92.00", ["soja"], True),
    ("Anticuchos", "parrilla", "Brochetas de corazón con papa y maní", "45.00", ["maní"], False),
    (
        "Silpancho",
        "criolla",
        "Milanesa con arroz, papas y huevo frito",
        "48.00",
        ["gluten", "huevo"],
        True,
    ),
    ("Chicharrón de cerdo", "criolla", "Cerdo frito con mote y chuño", "65.00", [], False),
    ("Sopa de maní", "entradas", "Sopa tradicional con papas fritas", "28.00", ["maní"], True),
    (
        "Empanada de queso",
        "entradas",
        "Empanada horneada rellena de queso",
        "12.00",
        ["gluten", "lácteos"],
        True,
    ),
    ("Jugo de maracuyá", "bebidas", "Jugo natural 500 ml", "15.00", [], True),
    ("Limonada", "bebidas", "Limonada con hierbabuena 500 ml", "14.00", [], True),
    ("Gaseosa", "bebidas", "Botella personal 350 ml", "10.00", [], True),
    ("Helado de canela", "postres", "Dos bolas con salsa de caramelo", "22.00", ["lácteos"], True),
]


async def seed_menu(session: AsyncSession) -> None:
    rows = [
        {
            "name": n,
            "category": c,
            "description": d,
            "price": Decimal(p),
            "allergens": a,
            "available": av,
        }
        for n, c, d, p, a, av in MENU
    ]
    stmt = insert(MenuItem).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[MenuItem.name],
        set_={
            k: stmt.excluded[k]
            for k in ("category", "description", "price", "allergens", "available")
        },
    )
    await session.execute(stmt)
    await session.commit()


async def main() -> None:
    async with SessionLocal() as session:
        await seed_menu(session)
    print(f"Menú sembrado: {len(MENU)} platos")


if __name__ == "__main__":
    asyncio.run(main())
