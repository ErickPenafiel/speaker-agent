from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.money import format_money
from app.db.models import MenuItem


async def list_items(
    session: AsyncSession, category: str | None = None, query: str | None = None
) -> list[MenuItem]:
    stmt = select(MenuItem).order_by(MenuItem.category, MenuItem.name)
    if category:
        stmt = stmt.where(MenuItem.category == category.lower())
    if query:
        stmt = stmt.where(MenuItem.name.ilike(f"%{query}%"))
    return list((await session.scalars(stmt)).all())


async def get_menu_tool(session: AsyncSession, args: dict, **_: object) -> str:
    """Respuesta corta y fácil de decir en voz alta."""
    items = await list_items(session, args.get("category"), args.get("query"))
    if not items:
        return "No encontré platos con ese criterio."
    parts = []
    for i in items:
        if not i.available:
            parts.append(f"{i.name}: agotado")
            continue
        allergens = f", contiene {', '.join(i.allergens)}" if i.allergens else ""
        parts.append(f"{i.name}, {format_money(i.price)}{allergens}")
    return "; ".join(parts) + "."
