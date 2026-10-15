from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capture import capture_payload
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.providers.retell import parse_call_event, verify_signature
from app.schemas.retell import RetellToolRequest
from app.services import call_service
from app.services.tool_runner import run_tool


async def verify_retell_signature(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    x_retell_signature: Annotated[str | None, Header()] = None,
) -> None:
    body = (await request.body()).decode()
    if not verify_signature(body, settings.retell_api_key, x_retell_signature or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")


router = APIRouter(
    prefix="/retell",
    tags=["retell"],
    dependencies=[Depends(verify_retell_signature), Depends(capture_payload)],
)


@router.post("/tools", response_class=PlainTextResponse)
async def handle_tool(
    payload: RetellToolRequest, session: Annotated[AsyncSession, Depends(get_session)]
) -> str:
    return await run_tool(
        session,
        payload.name,
        payload.args,
        call_id=payload.call.call_id if payload.call else None,
        tool_call_id=None,  # Retell no envía id por invocación; la idempotencia usará call_id+args
        session_id=payload.session_id,
    )


@router.post("/webhook")
async def handle_webhook(
    payload: Annotated[dict[str, Any], Body()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, bool]:
    """`call_ended` y `call_analyzed` se fusionan en una sola fila; otros eventos se ignoran (200).
    Retell reintenta hasta 3 veces: el upsert es idempotente."""
    report = parse_call_event(payload)
    if report is not None:
        await call_service.save_report(session, report)
    return {"ok": True}
