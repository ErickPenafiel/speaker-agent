"""Ejecución de una tool call, común a todos los proveedores de voz."""

import time

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.services.tool_registry import TOOLS

log = structlog.get_logger()

TECH_ERROR = "Hubo un problema técnico. Ofrece pasar con una persona."
UNKNOWN_TOOL = "Herramienta no disponible."


def flat(text: str) -> str:
    """Los proveedores esperan un string plano de una sola línea."""
    return " ".join(text.split())


SLOW_MS = 1000  # criterio de aceptación: las tools responden en < 1 s


async def run_tool(
    session: AsyncSession,
    name: str,
    arguments: dict,
    *,
    call_id: str | None,
    tool_call_id: str | None,
    session_id: str | None,
) -> str:
    """Una transacción por tool call: commit si va bien, rollback si falla. Nunca lanza.
    Se registra solo el nombre de la tool, el resultado (ok / business_error / ...) y la duración:
    jamás argumentos ni textos de respuesta, que pueden contener datos de clientes."""
    start = time.perf_counter()
    outcome = "ok"
    with structlog.contextvars.bound_contextvars(call_id=call_id, tool=name):
        handler = TOOLS.get(name)
        if handler is None:
            outcome, text = "unknown_tool", UNKNOWN_TOOL
        else:
            try:
                text = await handler(
                    session,
                    arguments,
                    call_id=call_id,
                    tool_call_id=tool_call_id,
                    session_id=session_id,
                )
                await session.commit()
            except BusinessError as e:
                await session.rollback()
                outcome, text = "business_error", str(e)
            except Exception:
                await session.rollback()
                outcome, text = "tech_error", TECH_ERROR
                log.exception("tool_failed")
        ms = round((time.perf_counter() - start) * 1000)
        emit = log.warning if ms > SLOW_MS or outcome == "tech_error" else log.info
        emit("tool_call", outcome=outcome, duration_ms=ms, slow=ms > SLOW_MS)
    return flat(text)
