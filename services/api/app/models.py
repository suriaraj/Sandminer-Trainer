import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BookingStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    QUOTE_CREATED = "QUOTE_CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    KYC_PENDING = "KYC_PENDING"
    CONFIRMED = "CONFIRMED"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    VEHICLE_HANDED_OVER = "VEHICLE_HANDED_OVER"
    RENTAL_ACTIVE = "RENTAL_ACTIVE"
    RETURN_PENDING = "RETURN_PENDING"
    VEHICLE_RETURNED = "VEHICLE_RETURNED"
    INSPECTION_PENDING = "INSPECTION_PENDING"
    SETTLEMENT_PENDING = "SETTLEMENT_PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    NO_SHOW = "NO_SHOW"
    DISPUTED = "DISPUTED"
    REFUND_PENDING = "REFUND_PENDING"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    REFUNDED = "REFUNDED"
    DISPUTED = "DISPUTED"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    mobile: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True)


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(120), unique=True)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True)


class Operator(Base, TimestampMixin):
    __tablename__ = "operators"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    legal_name: Mapped[str] = mapped_column(String(200))
    business_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="REGISTERED", index=True)


class OperatorUser(Base):
    __tablename__ = "operator_users"
    operator_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("operators.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)


class VehicleCategory(Base):
    __tablename__ = "vehicle_categories"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"
    __table_args__ = (
        Index("ix_vehicle_city_status_category", "city", "status", "category_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    operator_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("operators.id"), index=True)
    category_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("vehicle_categories.id"), index=True)
    registration_number: Mapped[str] = mapped_column(String(40), unique=True)
    brand: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(80))
    variant: Mapped[str | None] = mapped_column(String(80), nullable=True)
    city: Mapped[str] = mapped_column(String(100), index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    status: Mapped[str] = mapped_column(String(40), default="AVAILABLE", index=True)
    fuel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    transmission: Mapped[str | None] = mapped_column(String(40), nullable=True)
    seats: Mapped[int | None] = mapped_column(nullable=True)


class VehicleBlock(Base, TimestampMixin):
    __tablename__ = "vehicle_blocks"
    __table_args__ = (Index("ix_vehicle_block_window", "vehicle_id", "start_at", "end_at"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("vehicles.id"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(200))


class PricingPackage(Base, TimestampMixin):
    __tablename__ = "pricing_packages"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    operator_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("operators.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    service_type: Mapped[str] = mapped_column(String(60), default="SELF_DRIVE")
    duration_minutes: Mapped[int] = mapped_column()
    included_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    base_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=Decimal("0"))
    deposit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Quote(Base, TimestampMixin):
    __tablename__ = "quotes"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    vehicle_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("vehicles.id"), index=True)
    package_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pricing_packages.id"))
    pickup_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    return_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pricing_version: Mapped[str] = mapped_column(String(80))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    deposit: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    line_items: Mapped[dict] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_booking_vehicle_window", "vehicle_id", "pickup_at", "return_at"),
        Index("ix_booking_customer_status", "customer_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    operator_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("operators.id"), index=True)
    vehicle_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("vehicles.id"), index=True)
    quote_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("quotes.id"), unique=True)
    pickup_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    return_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), index=True)
    payment_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    currency: Mapped[str] = mapped_column(String(3))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class BookingStatusHistory(Base):
    __tablename__ = "booking_status_history"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bookings.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40))
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("provider", "provider_transaction_id", name="uq_payment_provider_txn"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bookings.id"), index=True)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    provider_transaction_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), index=True)


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (UniqueConstraint("provider", "provider_event_id", name="uq_payment_provider_event"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(80))
    provider_event_id: Mapped[str] = mapped_column(String(160))
    payload_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    scope: Mapped[str] = mapped_column(String(120))
    key: Mapped[str] = mapped_column(String(160))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_code: Mapped[int | None] = mapped_column(nullable=True)
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(160), index=True)
    entity: Mapped[str] = mapped_column(String(120), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    topic: Mapped[str] = mapped_column(String(120), index=True)
    aggregate_id: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
