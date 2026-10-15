from datetime import datetime
from typing import Any, Literal

from app.core.config import Settings
from app.providers.base import ProviderNotConfiguredError, WebCallInfo
from app.schemas.call_report import CallReport, aware, normalize_turns, session_from_metadata


class VapiProvider:
    name: Literal["vapi", "retell"] = "vapi"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_web_call(self, *, session_id: str, language: str, now: str) -> WebCallInfo:
        if not (self.settings.vapi_public_key and self.settings.vapi_assistant_id):
            raise ProviderNotConfiguredError("Faltan VAPI_PUBLIC_KEY / VAPI_ASSISTANT_ID")
        return WebCallInfo(
            provider="vapi",
            public_key=self.settings.vapi_public_key,
            assistant_id=self.settings.vapi_assistant_id,
            # El frontend lo pasa en assistantOverrides.metadata / variableValues al iniciar.
            metadata={"sessionId": session_id, "language": language, "now": now},
        )


def _iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return aware(datetime.fromisoformat(value))
    except ValueError:
        return None


def parse_end_of_call(message: dict[str, Any]) -> CallReport | None:
    """`end-of-call-report` de Vapi -> CallReport. Parser tolerante: la doc no fija del todo dónde
    van resumen y duración, así que se buscan en `analysis`, en `message` y en `artifact`."""
    if message.get("type") != "end-of-call-report":
        return None
    call = message.get("call") or {}
    call_id = call.get("id")
    if not call_id:
        return None
    artifact = message.get("artifact") or {}
    analysis = message.get("analysis") or {}

    turns = normalize_turns(
        artifact.get("messages") or message.get("messages"), text_keys=("message", "content")
    )
    summary = analysis.get("summary") or message.get("summary") or artifact.get("summary")
    started = _iso(message.get("startedAt") or call.get("startedAt") or call.get("createdAt"))
    ended = _iso(message.get("endedAt") or call.get("endedAt"))

    duration = message.get("durationSeconds")
    if isinstance(duration, int | float):
        duration = round(duration)
    elif started and ended:
        duration = round((ended - started).total_seconds())
    else:
        duration = None

    return CallReport(
        provider="vapi",
        provider_call_id=str(call_id)[:64],
        session_id=session_from_metadata(call.get("metadata") or message.get("metadata")),
        started_at=started,
        duration_seconds=duration,
        transcript=turns,
        summary=summary.strip() if isinstance(summary, str) and summary.strip() else None,
    )
