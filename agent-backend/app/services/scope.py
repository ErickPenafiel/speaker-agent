"""Visibilidad por visitante: cada uno ve sus datos; si no tiene ninguno, ve los de ejemplo."""

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import DEMO_SESSION


async def visible_session(session: AsyncSession, model, session_id: str) -> str:
    """Sesión cuyas filas se muestran en `model`: la del visitante o, si no tiene ninguna, la demo."""
    has_own = await session.scalar(select(exists().where(model.session_id == session_id)))
    return session_id if has_own else DEMO_SESSION
