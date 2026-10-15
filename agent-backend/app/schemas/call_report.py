from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class CallReport:
    """Reporte de fin de llamada normalizado, independiente del proveedor.
    Los campos `None` significan "no vienen en este evento" y no pisan lo ya guardado."""

    provider: str
    provider_call_id: str
    session_id: str | None = None
    started_at: datetime | None = None
    duration_seconds: int | None = None
    transcript: list[dict[str, str]] | None = None  # [{"role": "user"|"assistant", "text": ...}]
    summary: str | None = None


_ROLES = {
    "user": "user",
    "customer": "user",
    "assistant": "assistant",
    "bot": "assistant",
    "agent": "assistant",
}


def normalize_turns(raw: Any, *, text_keys: tuple[str, ...]) -> list[dict[str, str]] | None:
    """Convierte la lista de mensajes del proveedor en turnos user/assistant.
    Descarta system/tool/etc. y mensajes vacíos. None si no hay lista (dato ausente)."""
    if not isinstance(raw, list):
        return None
    turns = []
    for m in raw:
        if not isinstance(m, dict):
            continue
        role = _ROLES.get(str(m.get("role", "")).lower())
        text = next((m[k] for k in text_keys if isinstance(m.get(k), str)), "").strip()
        if role and text:
            turns.append({"role": role, "text": text})
    return turns


def session_from_metadata(metadata: Any) -> str | None:
    sid = metadata.get("sessionId") if isinstance(metadata, dict) else None
    return str(sid)[:64] if sid else None


def aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
