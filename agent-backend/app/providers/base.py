from typing import Literal, Protocol

from pydantic import BaseModel, Field


class ProviderNotConfiguredError(Exception):
    """Faltan credenciales del proveedor en el entorno."""


class ProviderApiError(Exception):
    """El proveedor respondió con error al crear la llamada."""


class WebCallInfo(BaseModel):
    """Lo que el frontend necesita para iniciar una llamada web con el proveedor activo."""

    provider: Literal["vapi", "retell"]
    # Vapi: el SDK arranca con clave pública + id del asistente
    public_key: str | None = None
    assistant_id: str | None = None
    # Retell: el servidor crea la llamada y entrega un token de un solo uso
    access_token: str | None = None
    call_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class VoiceProvider(Protocol):
    name: Literal["vapi", "retell"]

    async def create_web_call(self, *, session_id: str, language: str, now: str) -> WebCallInfo: ...
