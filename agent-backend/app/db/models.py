import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    allergens: Mapped[list[str]] = mapped_column(JSONB, default=list)
    available: Mapped[bool] = mapped_column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = _uuid_pk()
    number: Mapped[int] = mapped_column(Integer, Identity(start=1), unique=True)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    call_id: Mapped[str | None] = mapped_column(String(64), index=True)
    customer_name: Mapped[str] = mapped_column(String(80))
    customer_phone: Mapped[str | None] = mapped_column(String(32))
    type: Mapped[str] = mapped_column(String(16))  # pickup | delivery
    address: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="confirmed")
    notes: Mapped[str | None] = mapped_column(Text)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = _created_at()

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    menu_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("menu_items.id"))
    name: Mapped[str] = mapped_column(String(120))  # copia al momento del pedido
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    options: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)

    order: Mapped[Order] = relationship(back_populates="items")


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    call_id: Mapped[str | None] = mapped_column(String(64), index=True)
    customer_name: Mapped[str] = mapped_column(String(80))
    party_size: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)
    time: Mapped[time] = mapped_column(Time)
    notes: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = _created_at()


class Call(Base):
    __tablename__ = "calls"
    __table_args__ = (
        UniqueConstraint("provider", "provider_call_id", name="uq_calls_provider_call"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    provider: Mapped[str] = mapped_column(String(16))  # vapi | retell
    provider_call_id: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    # none_as_null: None se guarda como NULL de SQL (no como JSON null) para poder fusionar reportes
    transcript: Mapped[list | None] = mapped_column(JSONB(none_as_null=True))
    summary: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(
        String(16)
    )  # order|reservation|info|transferred|abandoned
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[uuid.UUID] = _uuid_pk()
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    call_id: Mapped[str | None] = mapped_column(String(64), index=True)
    reason: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = _created_at()
