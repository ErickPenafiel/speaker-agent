import datetime as dt
import uuid
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, computed_field

from app.core.session import DEMO_SESSION

_TIME_FORMATS = ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p")


def _parse_time(v: Any) -> Any:
    """Acepta "20:00", "20:00:00", "8:00 PM", "8pm". Una hora suelta ("8") es ambigua: se rechaza."""
    if isinstance(v, str):
        s = v.strip().lower().replace(".", "")
        for fmt in _TIME_FORMATS:
            try:
                return dt.datetime.strptime(s, fmt).time()
            except ValueError:
                continue
    return v


class CreateReservationArgs(BaseModel):
    customer_name: str = Field(min_length=2, max_length=80)
    party_size: int = Field(ge=1, le=500)  # el máximo real (config) se valida en el servicio
    date: dt.date = Field(description="YYYY-MM-DD")
    time: Annotated[dt.time, BeforeValidator(_parse_time)] = Field(description="HH:MM, 24 horas")
    notes: str | None = Field(default=None, max_length=300)


class TransferArgs(BaseModel):
    reason: str = Field(default="no especificado", max_length=300)


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: str | None = Field(default=None, exclude=True)
    call_id: str | None
    customer_name: str
    party_size: int
    date: dt.date
    time: dt.time
    notes: str | None
    created_at: dt.datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_demo(self) -> bool:
        return self.session_id == DEMO_SESSION
