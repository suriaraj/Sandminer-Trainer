from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models import TimestampMixin


class KycCase(Base, TimestampMixin):
    __tablename__ = "kyc_cases"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    country_code: Mapped[str] = mapped_column(String(2))
    service_type: Mapped[str] = mapped_column(String(60))
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="PENDING", index=True)
    reviewer_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KycDocument(Base, TimestampMixin):
    __tablename__ = "kyc_documents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    kyc_case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("kyc_cases.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(80))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(120))
    file_size: Mapped[int] = mapped_column()
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40), default="UPLOADED")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Deposit(Base, TimestampMixin):
    __tablename__ = "deposits"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bookings.id"), unique=True, index=True)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(40), default="PENDING", index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)


class DepositTransaction(Base):
    __tablename__ = "deposit_transactions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    deposit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("deposits.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    reference: Mapped[str] = mapped_column(String(160), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HandoverRecord(Base):
    __tablename__ = "handover_records"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bookings.id"), unique=True, index=True)
    odometer: Mapped[Decimal] = mapped_column(Numeric(12, 1))
    fuel_level_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    condition: Mapped[dict] = mapped_column(JSONB)
    accessories: Mapped[dict] = mapped_column(JSONB)
    acknowledgement_method: Mapped[str] = mapped_column(String(40))
    acknowledged_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InspectionRecord(Base):
    __tablename__ = "inspection_records"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bookings.id"), unique=True, index=True)
    odometer: Mapped[Decimal] = mapped_column(Numeric(12, 1))
    fuel_level_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    condition: Mapped[dict] = mapped_column(JSONB)
    accessories: Mapped[dict] = mapped_column(JSONB)
    additional_km: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    late_minutes: Mapped[int] = mapped_column(default=0)
    created_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DamageRecord(Base, TimestampMixin):
    __tablename__ = "damage_records"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bookings.id"), index=True)
    vehicle_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("vehicles.id"), index=True)
    location: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(1000))
    severity: Mapped[str] = mapped_column(String(40))
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    approved_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="REPORTED", index=True)


class Settlement(Base, TimestampMixin):
    __tablename__ = "settlements"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bookings.id"), unique=True, index=True)
    operator_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("operators.id"), index=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    platform_commission: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    taxes: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    adjustments: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    refunds: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    net_payable: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(40), default="PENDING", index=True)


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reference_type: Mapped[str] = mapped_column(String(60))
    reference_id: Mapped[str] = mapped_column(String(80), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    description: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ledger_transactions.id"), index=True)
    account_code: Mapped[str] = mapped_column(String(120), index=True)
    direction: Mapped[str] = mapped_column(String(10))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("booking_id", "customer_id", name="uq_review_booking_customer"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bookings.id"), index=True)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    overall_rating: Mapped[int] = mapped_column()
    vehicle_rating: Mapped[int | None] = mapped_column(nullable=True)
    operator_rating: Mapped[int | None] = mapped_column(nullable=True)
    driver_rating: Mapped[int | None] = mapped_column(nullable=True)
    comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(40), default="VISIBLE")


class SupportTicket(Base, TimestampMixin):
    __tablename__ = "support_tickets"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    booking_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(60))
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")
    subject: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(40), default="OPEN", index=True)
    assigned_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    channel: Mapped[str] = mapped_column(String(40))
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), default="PENDING", index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
