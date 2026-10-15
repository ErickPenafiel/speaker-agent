from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capture import capture_payload
from app.core.security import verify_vapi_secret
from app.db.session import get_session
from app.providers.vapi import parse_end_of_call
from app.schemas.vapi import ToolResponse, ToolResult, VapiRequest, VapiWebhook
from app.services import call_service
from app.services.tool_runner import run_tool

router = APIRouter(
    prefix="/vapi",
    tags=["vapi"],
    dependencies=[Depends(verify_vapi_secret), Depends(capture_payload)],  # primero la auth
)


@router.post("/tools", response_model=ToolResponse)
async def handle_tools(
    payload: VapiRequest, session: Annotated[AsyncSession, Depends(get_session)]
) -> ToolResponse:
    msg = payload.message
    if msg.type != "tool-calls":
        return ToolResponse()
    call_id = msg.call.id if msg.call else None
    results = [
        ToolResult(
            toolCallId=tc.id,
            result=await run_tool(
                session,
                tc.name,
                tc.arguments,
                call_id=call_id,
                tool_call_id=tc.id,
                session_id=msg.session_id,
            ),
        )
        for tc in msg.tool_calls
    ]
    return ToolResponse(results=results)


@router.post("/webhook")
async def handle_webhook(
    payload: VapiWebhook, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, bool]:
    """Server messages de Vapi. Solo `end-of-call-report` se guarda; el resto se ignora (200)."""
    report = parse_end_of_call(payload.message)
    if report is not None:
        await call_service.save_report(session, report)
    return {"ok": True}
