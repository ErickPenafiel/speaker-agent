import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


async def verify_vapi_secret(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_vapi_secret: Annotated[str | None, Header()] = None,
) -> None:
    """Acepta `Authorization: Bearer <secreto>` o el header heredado `X-Vapi-Secret`
    (ambos documentados por Vapi; depende de la credencial configurada en su dashboard)."""
    candidate = x_vapi_secret
    if not candidate and authorization and authorization.lower().startswith("bearer "):
        candidate = authorization[7:].strip()
    if not candidate or not hmac.compare_digest(candidate, settings.vapi_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")
