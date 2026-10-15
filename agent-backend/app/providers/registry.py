from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.providers.base import VoiceProvider
from app.providers.retell import RetellProvider
from app.providers.vapi import VapiProvider


def get_voice_provider(settings: Annotated[Settings, Depends(get_settings)]) -> VoiceProvider:
    return (
        RetellProvider(settings) if settings.voice_provider == "retell" else VapiProvider(settings)
    )
