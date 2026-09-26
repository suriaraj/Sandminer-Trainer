from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class OperatorCreateRequest(BaseModel):
    legal_name: str = Field(min_length=2, max_length=200)
    business_name: str = Field(min_length=2, max_length=200)


class OperatorResponse(BaseModel):
    id: UUID
    legal_name: str
    business_name: str
    status: str


class VehicleCreateRequest(BaseModel):
    operator_id: UUID
    category_id: UUID
    registration_number: str = Field(min_length=3, max_length=40)
    brand: str = Field(min_length=2, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    variant: str | None = Field(default=None, max_length=80)
    city: str = Field(min_length=2, max_length=100)
    timezone: str = Field(min_length=3, max_length=64)
    fuel: str | None = Field(default=None, max_length=40)
    transmission: str | None = Field(default=None, max_length=40)
    seats: int | None = Field(default=None, ge=1, le=80)


class VehicleResponse(BaseModel):
    id: UUID
    operator_id: UUID
    category_id: UUID
    registration_number: str
    brand: str
    model: str
    variant: str | None
    city: str
    timezone: str
    status: str
    fuel: str | None
    transmission: str | None
    seats: int | None


class VehicleStatusRequest(BaseModel):
    status: Literal[
        "AVAILABLE", "RESERVED", "BOOKED", "RENTED", "UNDER_INSPECTION",
        "MAINTENANCE", "BLOCKED", "INACTIVE", "RETIRED"
    ]


class PricingPackageCreateRequest(BaseModel):
    operator_id: UUID
    name: str = Field(min_length=2, max_length=160)
    service_type: Literal["SELF_DRIVE", "CHAUFFEUR_PACKAGE", "AIRPORT_TRANSFER", "OUTSTATION_ONE_WAY", "OUTSTATION_ROUND_TRIP", "CUSTOM_DURATION"]
    duration_minutes: int = Field(gt=0)
    included_km: Decimal = Field(ge=0)
    base_price: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    deposit: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)


class PricingPackageResponse(BaseModel):
    id: UUID
    operator_id: UUID
    name: str
    service_type: str
    duration_minutes: int
    included_km: Decimal
    base_price: Decimal
    tax_rate: Decimal
    deposit: Decimal
    currency: str
    active: bool


class AvailabilityPolicyRequest(BaseModel):
    pre_buffer_minutes: int = Field(ge=0, le=1440)
    post_buffer_minutes: int = Field(ge=0, le=1440)


class AvailabilityPolicyResponse(BaseModel):
    operator_id: UUID
    pre_buffer_minutes: int
    post_buffer_minutes: int


class OperatorStatusRequest(BaseModel):
    status: Literal["REGISTERED", "UNDER_REVIEW", "APPROVED", "ACTIVE", "SUSPENDED", "INACTIVE"]


class AdminKpiResponse(BaseModel):
    total_users: int
    total_operators: int
    total_vehicles: int
    available_vehicles: int
    total_bookings: int
    active_rentals: int
    captured_revenue: Decimal
    pending_kyc: int
