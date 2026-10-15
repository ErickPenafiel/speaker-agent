import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, computed_field, model_validator

from app.core.session import DEMO_SESSION


class OrderStatus(StrEnum):
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"


# confirmed -> preparing -> ready
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.confirmed: {OrderStatus.preparing},
    OrderStatus.preparing: {OrderStatus.ready},
    OrderStatus.ready: set(),
}

_TYPE_ALIASES = {
    "recoger": "pickup",
    "retiro": "pickup",
    "retirar": "pickup",
    "para llevar": "pickup",
    "domicilio": "delivery",
    "envio": "delivery",
    "envío": "delivery",
    "a domicilio": "delivery",
}


def _normalize_type(v: Any) -> Any:
    if isinstance(v, str):
        v = v.strip().lower()
        return _TYPE_ALIASES.get(v, v)
    return v


# ---------- Argumentos de la tool create_order ----------


class OrderItemIn(BaseModel):
    id: uuid.UUID | None = Field(default=None, description="id del plato devuelto por get_menu")
    name: str | None = Field(default=None, description="nombre del plato si no se tiene el id")
    quantity: int = Field(default=1, ge=1, le=20)
    options: dict[str, Any] | None = None
    notes: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _needs_id_or_name(self) -> "OrderItemIn":
        if not self.id and not (self.name and self.name.strip()):
            raise ValueError("cada plato necesita nombre o id")
        return self


class CreateOrderArgs(BaseModel):
    customer_name: str = Field(min_length=2, max_length=80)
    type: Annotated[Literal["pickup", "delivery"], BeforeValidator(_normalize_type)]
    address: str | None = Field(default=None, max_length=300)
    items: list[OrderItemIn] = Field(min_length=1, max_length=30)
    notes: str | None = Field(default=None, max_length=300)
    customer_confirmed: bool = Field(
        default=False,
        description="true solo si el cliente confirmó en voz alta el resumen del pedido",
    )


# ---------- Panel ----------


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    quantity: int
    unit_price: Decimal
    options: dict[str, Any] | None
    notes: str | None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: int
    session_id: str | None = Field(default=None, exclude=True)
    call_id: str | None
    customer_name: str
    type: Literal["pickup", "delivery"]
    address: str | None
    status: OrderStatus
    notes: str | None
    total: Decimal
    created_at: datetime
    items: list[OrderItemOut]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_demo(self) -> bool:
        return self.session_id == DEMO_SESSION


class StatusIn(BaseModel):
    status: OrderStatus
