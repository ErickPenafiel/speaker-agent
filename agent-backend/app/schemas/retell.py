from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RetellCall(BaseModel):
    model_config = ConfigDict(extra="allow")

    call_id: str | None = None
    metadata: dict[str, Any] | None = None


class RetellToolRequest(BaseModel):
    """Cuerpo por defecto de una custom function de Retell (no el modo "args only")."""

    model_config = ConfigDict(extra="allow")

    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    call: RetellCall | None = None

    @property
    def session_id(self) -> str | None:
        sid = ((self.call.metadata if self.call else None) or {}).get("sessionId")
        return str(sid)[:64] if sid else None
