"""Retell: firma de webhooks/funciones y creación de llamadas web."""

import hashlib
import hmac
import re
import time
from datetime import UTC, datetime
from typing import Any, Literal

import httpx

from app.core.config import Settings
from app.providers.base import ProviderApiError, ProviderNotConfiguredError, WebCallInfo
from app.schemas.call_report import CallReport, normalize_turns, session_from_metadata

SIGNATURE_RE = re.compile(r"v=(\d+),d=([0-9a-f]{64})")
TOLERANCE_MS = 5 * 60 * 1000


def verify_signature(body: str, api_key: str, signature: str, *, now_ms: int | None = None) -> bool:
    """`X-Retell-Signature: v=<ms>,d=<hex>` con d = HMAC-SHA256(api_key, body + <ms>).
    Mismo esquema que el SDK oficial; `body` es el cuerpo crudo, sin re-serializar."""
    m = SIGNATURE_RE.fullmatch(signature or "")
    if not m or not api_key:
        return False
    ts, digest = m.group(1), m.group(2)
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    if abs(now_ms - int(ts)) > TOLERANCE_MS:
        return False
    expected = hmac.new(api_key.encode(), (body + ts).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, digest)


class RetellProvider:
    name: Literal["vapi", "retell"] = "retell"

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    async def create_web_call(self, *, session_id: str, language: str, now: str) -> WebCallInfo:
        s = self.settings
        if not (s.retell_api_key and s.retell_agent_id):
            raise ProviderNotConfiguredError("Faltan RETELL_API_KEY / RETELL_AGENT_ID")
        metadata = {"sessionId": session_id, "language": language}
        payload = {
            "agent_id": s.retell_agent_id,
            "metadata": metadata,
            "retell_llm_dynamic_variables": {"language": language, "now": now},
        }
        async with httpx.AsyncClient(
            base_url=s.retell_api_base, transport=self.transport, timeout=10
        ) as client:
            try:
                r = await client.post(
                    "/v3/create-web-call",
                    json=payload,
                    headers={"Authorization": f"Bearer {s.retell_api_key}"},
                )
                r.raise_for_status()
            except httpx.HTTPError as e:
                raise ProviderApiError(f"Retell create-web-call falló: {e}") from e
        data = r.json()
        return WebCallInfo(
            provider="retell",
            access_token=data["access_token"],
            call_id=data.get("call_id"),
            metadata=metadata,
        )


def parse_call_event(payload: dict[str, Any]) -> CallReport | None:
    """Webhook de Retell (`call_ended` / `call_analyzed`) -> CallReport.
    `call_ended` trae transcripción y tiempos pero no `call_analysis`; `call_analyzed` lo añade.
    Los campos ausentes quedan en None y no pisan lo ya guardado."""
    if payload.get("event") not in ("call_ended", "call_analyzed"):
        return None
    call = payload.get("call") or {}
    call_id = call.get("call_id")
    if not call_id:
        return None

    start_ms, end_ms, duration_ms = (
        call.get("start_timestamp"),
        call.get("end_timestamp"),
        call.get("duration_ms"),
    )
    if (
        not isinstance(duration_ms, int | float)
        and isinstance(start_ms, int)
        and isinstance(end_ms, int)
    ):
        duration_ms = end_ms - start_ms
    summary = (call.get("call_analysis") or {}).get("call_summary")

    return CallReport(
        provider="retell",
        provider_call_id=str(call_id)[:64],
        session_id=session_from_metadata(call.get("metadata")),
        started_at=datetime.fromtimestamp(start_ms / 1000, UTC)
        if isinstance(start_ms, int)
        else None,
        duration_seconds=round(duration_ms / 1000)
        if isinstance(duration_ms, int | float)
        else None,
        transcript=normalize_turns(call.get("transcript_object"), text_keys=("content",)),
        summary=summary.strip() if isinstance(summary, str) and summary.strip() else None,
    )
