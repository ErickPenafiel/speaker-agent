from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter(tags=["health"])
log = structlog.get_logger()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: instantáneo, no toca la base de datos."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    """Readiness: comprueba la base de datos. Úsalo para calentar el servicio y Neon (que se
    suspende solo) antes de una demo."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        log.warning("readiness_failed", exc_info=True)
        raise HTTPException(status_code=503, detail="Base de datos no disponible") from None
    return {"status": "ok", "db": "ok"}
