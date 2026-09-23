from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class KycCaseCreateRequest(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)
    service_type: str = Field(min_length=2, max_length=60)


class KycCaseResponse(BaseModel):
    id: UUID
    status: str
    country_code: str
    service_type: str
    provider: str | None
    reason: str | None
    verified_at: datetime | None
    expires_at: datetime | None


class KycReviewRequest(BaseModel):
    decision: Literal["VERIFIED", "REJECTED", "REQUIRED_AGAIN"]
    reason: str | None = Field(default=None, max_length=500)
    expires_at: datetime | None = None


class BookingTransitionRequest(BaseModel):
    target_status: str


class PaymentInitiateResponse(BaseModel):
    payment_id: UUID
    provider: str
    provider_reference: str
    status: str


class SandboxWebhookEvent(BaseModel):
    event_id: str = Field(min_length=8, max_length=160)
    transaction_id: str = Field(min_length=8, max_length=160)
    status: Literal["PENDING", "AUTHORIZED", "CAPTURED", "FAILED"]


class HandoverCreateRequest(BaseModel):
    odometer: Decimal = Field(ge=0)
    fuel_level_percent: Decimal = Field(ge=0, le=100)
    condition: dict
    accessories: dict = Field(default_factory=dict)
    acknowledgement_method: Literal["OTP", "DIGITAL_ACCEPTANCE"]
    acknowledged_by_user_id: UUID | None = None


class HandoverResponse(BaseModel):
    id: UUID
    booking_id: UUID
    odometer: Decimal
    fuel_level_percent: Decimal
    created_at: datetime


class InspectionCreateRequest(BaseModel):
    odometer: Decimal = Field(ge=0)
    fuel_level_percent: Decimal = Field(ge=0, le=100)
    condition: dict
    accessories: dict = Field(default_factory=dict)
    additional_km: Decimal = Field(default=Decimal("0"), ge=0)
    late_minutes: int = Field(default=0, ge=0)


class InspectionResponse(BaseModel):
    id: UUID
    booking_id: UUID
    odometer: Decimal
    fuel_level_percent: Decimal
    additional_km: Decimal
    late_minutes: int
    created_at: datetime


class DamageCreateRequest(BaseModel):
    location: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=2, max_length=1000)
    severity: Literal["MINOR", "MODERATE", "MAJOR", "CRITICAL"]
    estimated_cost: Decimal = Field(default=Decimal("0"), ge=0)


class DamageResponse(BaseModel):
    id: UUID
    booking_id: UUID
    status: str
    severity: str
    estimated_cost: Decimal


class ReviewCreateRequest(BaseModel):
    overall_rating: int = Field(ge=1, le=5)
    vehicle_rating: int | None = Field(default=None, ge=1, le=5)
    operator_rating: int | None = Field(default=None, ge=1, le=5)
    driver_rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    id: UUID
    booking_id: UUID
    overall_rating: int
    moderation_status: str


class SupportTicketCreateRequest(BaseModel):
    booking_id: UUID | None = None
    category: Literal[
        "PAYMENT", "BOOKING", "CANCELLATION", "VEHICLE", "OPERATOR",
        "DRIVER", "KYC", "DAMAGE", "DEPOSIT", "TECHNICAL", "OTHER"
    ]
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = "NORMAL"
    subject: str = Field(min_length=3, max_length=240)


class SupportTicketResponse(BaseModel):
    id: UUID
    booking_id: UUID | None
    category: str
    priority: str
    subject: str
    status: str


class DepositResponse(BaseModel):
    id: UUID
    booking_id: UUID
    amount: Decimal
    currency: str
    status: str
