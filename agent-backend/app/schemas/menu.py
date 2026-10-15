import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    description: str | None
    price: Decimal
    allergens: list[str]
    available: bool
