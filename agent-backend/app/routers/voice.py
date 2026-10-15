from datetime import datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.limits import limiter, web_call_cap, web_call_limit
from app.core.session import SESSION_ID_PATTERN
from app.providers.base import (
    ProviderApiError,
    ProviderNotConfiguredError,
    VoiceProvider,
    WebCallInfo,
)
from app.providers.registry import get_voice_provider

router = APIRouter(prefix="/voice", tags=["voice"])


class ConfigOut(BaseModel):
    provider: Literal["vapi", "retell"]


class WebCallIn(BaseModel):
    session_id: str = Field(pattern=SESSION_ID_PATTERN)
    language: Literal["es", "en"] = "es"


@router.get("/config", response_model=ConfigOut)
async def voice_config(settings: Annotated[Settings, Depends(get_settings)]) -> ConfigOut:
    return ConfigOut(provider=settings.voice_provider)


@router.post("/web-call", response_model=WebCallInfo, response_model_exclude_none=True)
@limiter.limit(web_call_limit)
async def create_web_call(
    request: Request,
    body: WebCallIn,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[VoiceProvider, Depends(get_voice_provider)],
) -> WebCallInfo:
    local_now = datetime.now(ZoneInfo(settings.timezone))
    if not web_call_cap.hit(settings.web_call_daily_cap, local_now.date()):
        raise HTTPException(429, detail="Se alcanzó el límite diario de llamadas de la demo")
    now = local_now.strftime("%A %Y-%m-%d %H:%M")
    try:
        return await provider.create_web_call(
            session_id=body.session_id, language=body.language, now=now
        )
    except ProviderNotConfiguredError as e:
        raise HTTPException(503, detail=str(e)) from e
    except ProviderApiError as e:
        raise HTTPException(502, detail="El proveedor de voz no respondió") from e
