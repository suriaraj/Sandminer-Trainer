from datetime import datetime
from typing import Literal
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class QuoteCreateRequest(BaseModel):
    vehicle_id: UUID
    package_id: UUID
    pickup_at: datetime
    return_at: datetime
    service_type: Literal[
        "SELF_DRIVE", "CHAUFFEUR_PACKAGE", "AIRPORT_TRANSFER",
        "OUTSTATION_ONE_WAY", "OUTSTATION_ROUND_TRIP", "CUSTOM_DURATION"
    ]
    pickup_location: str = Field(min_length=2, max_length=500)
    return_location: str = Field(min_length=2, max_length=500)
    booking_timezone: str = Field(min_length=3, max_length=64)
    coupon_code: str | None = None

    @model_validator(mode="after")
    def validate_window(self):
        if self.pickup_at.tzinfo is None or self.return_at.tzinfo is None:
            raise ValueError("pickup_at and return_at must include a timezone")
        if self.return_at <= self.pickup_at:
            raise ValueError("return_at must be after pickup_at")
        return self


class QuoteResponse(BaseModel):
    id: UUID
    vehicle_id: UUID
    currency: str
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    deposit: Decimal
    total: Decimal
    expires_at: datetime
    line_items: dict


class BookingCreateRequest(BaseModel):
    quote_id: UUID


class BookingResponse(BaseModel):
    id: UUID
    booking_number: str
    vehicle_id: UUID
    pickup_at: datetime
    return_at: datetime
    status: str
    currency: str
    total_amount: Decimal
    deposit_amount: Decimal


class VehicleSearchItem(BaseModel):
    id: UUID
    brand: str
    model: str
    variant: str | None
    city: str
    fuel: str | None
    transmission: str | None
    seats: int | None
