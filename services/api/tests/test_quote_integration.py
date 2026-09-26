"""Integration coverage for service-specific multi-unit pricing and quote persistence."""
import os
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.config import get_settings
from app.main import app
from app.models import Operator, PricingPackage, Vehicle, VehicleCategory


@pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="Requires migrated test database")
def test_two_day_quote_prices_two_package_units():
    now = datetime.now(UTC)
    operator = Operator(
        id=uuid4(), legal_name="Integration Fleet", business_name="Integration Fleet",
        status="ACTIVE", created_at=now, updated_at=now,
    )
    with SessionLocal() as db:
        category = db.scalar(select(VehicleCategory).where(VehicleCategory.code == "SEDAN"))
        assert category is not None
        db.add(operator)
        db.flush()
        vehicle = Vehicle(
            id=uuid4(), operator_id=operator.id, category_id=category.id,
            registration_number="QUOTE-" + uuid4().hex[:12],
            brand="Sample", model="Sedan", city="Chennai",
            timezone="Asia/Kolkata", status="AVAILABLE",
            created_at=now, updated_at=now,
        )
        package = PricingPackage(
            id=uuid4(), operator_id=operator.id, name="24 Hours",
            service_type="SELF_DRIVE", duration_minutes=1440,
            included_km=Decimal(200), base_price=Decimal("2000"),
            tax_rate=Decimal("0.18"), deposit=Decimal(4000),
            currency="INR", active=True, created_at=now, updated_at=now,
        )
        db.add_all([vehicle, package])
        db.commit()

    with TestClient(app) as client:
        result = client.post("/api/v1/auth/register", json={
            "email": "quote-" + uuid4().hex + "@example.com",
            "full_name": "Rental Test", "password": "QuoteTestPassword123!",
        })
        assert result.status_code == 201, result.text
        token = result.json()["access_token"]
        pickup = now + timedelta(days=4)
        headers = {"Authorization": "Bearer " + token}
        request_body = {
            "vehicle_id": str(vehicle.id), "package_id": str(package.id),
            "pickup_at": pickup.isoformat(),
            "return_at": (pickup + timedelta(days=2)).isoformat(),
            "service_type": "SELF_DRIVE",
            "pickup_location": "Chennai", "return_location": "Chennai",
            "booking_timezone": "Asia/Kolkata",
        }
        response = client.post("/api/v1/quotes", headers=headers, json=request_body)
        assert response.status_code == 201, response.text
        data = response.json()
        assert Decimal(data["subtotal"]) == Decimal(4000)
        assert Decimal(data["tax"]) == Decimal(720)
        assert Decimal(data["total"]) == Decimal(4720)
        assert Decimal(data["deposit"]) == Decimal(4000)
        assert data["line_items"]["package_units"] == 2

        request_body["service_type"] = "CHAUFFEUR_PACKAGE"
        mismatch = client.post("/api/v1/quotes", headers=headers, json=request_body)
        assert mismatch.status_code == 409

        request_body["service_type"] = "SELF_DRIVE"
        request_body["return_at"] = (pickup + timedelta(hours=36)).isoformat()
        mismatch = client.post("/api/v1/quotes", headers=headers, json=request_body)
        assert mismatch.status_code == 409

        booking_key = "booking-" + uuid4().hex
        booked = client.post(
            "/api/v1/bookings",
            headers={**headers, "Idempotency-Key": booking_key},
            json={"quote_id": data["id"]},
        )
        assert booked.status_code == 201, booked.text
        booking_id = booked.json()["id"]
        repeated = client.post(
            "/api/v1/bookings",
            headers={**headers, "Idempotency-Key": booking_key},
            json={"quote_id": data["id"]},
        )
        assert repeated.status_code == 201
        assert repeated.json()["id"] == booking_id

        started = client.post(
            f"/api/v1/bookings/{booking_id}/payments",
            headers={**headers, "Idempotency-Key": "pay-" + uuid4().hex},
        )
        assert started.status_code == 201, started.text
        assert started.json()["status"] == "PENDING"

        event = {
            "event_id": uuid4().hex,
            "transaction_id": started.json()["provider_reference"],
            "status": "CAPTURED",
        }
        raw = json.dumps(event, separators=(",", ":")).encode()
        signature = hmac.new(
            get_settings().payment_secret.encode(), raw, hashlib.sha256
        ).hexdigest()
        callback = client.post(
            "/api/v1/payments/webhooks/sandbox",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Payment-Signature": signature,
            },
        )
        assert callback.status_code == 200, callback.text
        assert callback.json() == {"success": True, "duplicate": False}
        duplicate = client.post(
            "/api/v1/payments/webhooks/sandbox",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Payment-Signature": signature,
            },
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["duplicate"] is True
        booking_after = client.get(
            f"/api/v1/bookings/{booking_id}", headers=headers
        )
        assert booking_after.json()["status"] == "KYC_PENDING"
