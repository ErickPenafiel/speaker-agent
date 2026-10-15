from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.db.models import Transfer
from app.schemas.reservations import TransferArgs
from app.services.idempotency import idempotency_key, insert_once

MESSAGE = (
    "Transferencia registrada. Dile al cliente que lo comunicas con una persona del "
    "restaurante y despídete brevemente."
)


async def transfer_tool(
    session: AsyncSession,
    args: dict,
    *,
    call_id: str | None = None,
    tool_call_id: str | None = None,
    session_id: str | None = None,
) -> str:
    """Demo: solo registra la solicitud (la transferencia real a un número es opcional en el proveedor)."""
    try:
        data = TransferArgs(**args)
    except (ValidationError, TypeError):
        raise BusinessError(
            "No entendí el motivo. Pregunta por qué desea hablar con una persona."
        ) from None
    transfer = Transfer(
        session_id=session_id,
        call_id=call_id,
        reason=data.reason.strip() or "no especificado",
        idempotency_key=idempotency_key(call_id, tool_call_id, args, scope="transfer"),
    )
    await insert_once(session, transfer, Transfer)
    return MESSAGE
