"""Payloads de Vapi (server messages). Parser tolerante: según la doc vigente la tool call
llega como `function.{name,arguments}` o con `name` y `parameters` al mismo nivel; `arguments`
puede ser objeto o string JSON."""

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        fn = data.get("function") or {}
        name = fn.get("name") or data.get("name")
        raw = fn.get("arguments")
        if raw is None:
            raw = data.get("arguments", data.get("parameters"))
        if isinstance(raw, str):
            try:
                raw = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                raw = {}
        return {"id": data.get("id"), "name": name, "arguments": raw or {}}


class VapiCall(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    metadata: dict[str, Any] | None = None


class VapiMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    call: VapiCall | None = None
    toolCallList: list[ToolCall] = Field(default_factory=list)
    toolWithToolCallList: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def tool_calls(self) -> list[ToolCall]:
        if self.toolCallList:
            return self.toolCallList
        # Forma anidada: [{"name": ..., "toolCall": {"id": ..., "parameters": {...}}}]
        calls = []
        for t in self.toolWithToolCallList:
            tc = t.get("toolCall") or {}
            calls.append(ToolCall.model_validate({"name": t.get("name"), **tc}))
        return calls

    @property
    def session_id(self) -> str | None:
        meta = (self.call.metadata if self.call else None) or {}
        sid = meta.get("sessionId")
        return str(sid)[:64] if sid else None


class VapiRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    message: VapiMessage


class ToolResult(BaseModel):
    toolCallId: str
    result: str


class ToolResponse(BaseModel):
    results: list[ToolResult] = Field(default_factory=list)


class VapiWebhook(BaseModel):
    """Cualquier server message; el parser decide qué hacer según `message.type`."""

    model_config = ConfigDict(extra="allow")

    message: dict[str, Any]
