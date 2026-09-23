from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AvailabilityPolicy(Base):
    __tablename__ = "availability_policies"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    scope_key: Mapped[str] = mapped_column(String(120), unique=True)
    operator_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("operators.id"), nullable=True, index=True
    )
    pre_buffer_minutes: Mapped[int] = mapped_column(Integer)
    post_buffer_minutes: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VehicleReservation(Base):
    __tablename__ = "vehicle_reservations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("bookings.id"), unique=True, index=True
    )
    vehicle_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("vehicles.id"), index=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RentalConfiguration(Base):
    __tablename__ = "rental_configurations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    quote_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("quotes.id"), unique=True, index=True
    )
    booking_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("bookings.id"), unique=True, nullable=True, index=True
    )
    service_type: Mapped[str] = mapped_column(String(60), index=True)
    pickup_location: Mapped[str] = mapped_column(String(500))
    return_location: Mapped[str] = mapped_column(String(500))
    booking_timezone: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
