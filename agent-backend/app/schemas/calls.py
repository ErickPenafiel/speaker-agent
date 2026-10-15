import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.core.session import DEMO_SESSION
from app.schemas.orders import OrderOut
from app.schemas.reservations import ReservationOut

Outcome = Literal["order", "reservation", "transferred", "info", "abandoned"]


class TranscriptTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class CallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: str | None = Field(default=None, exclude=True)
    provider: Literal["vapi", "retell"]
    provider_call_id: str
    started_at: datetime | None
    duration_seconds: int | None
    outcome: Outcome | None
    summary: str | None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_demo(self) -> bool:
        return self.session_id == DEMO_SESSION


class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reason: str
    created_at: datetime


class CallDetailOut(CallOut):
    transcript: list[TranscriptTurn]
    orders: list[OrderOut]
    reservations: list[ReservationOut]
    transfers: list[TransferOut]
