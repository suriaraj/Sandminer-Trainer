"""PostgreSQL integration: a racing booking for one exact vehicle never double-books."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.errors import ConflictError
from app.marketplace_models import RentalConfiguration
from app.models import (
    Booking,
    Operator,
    PricingPackage,
    Quote,
    User,
    Vehicle,
    VehicleCategory,
)
from app.services.booking import create_booking_from_quote


@pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="Requires migrated test PostgreSQL")
def test_concurrent_exact_vehicle_booking_allows_one_winner():
    now = datetime.now(UTC)
    pickup = now + timedelta(days=3)
    returned = pickup + timedelta(days=1)
    with SessionLocal() as db:
        category = db.scalar(
            select(VehicleCategory).where(VehicleCategory.code == "SEDAN")
        )
        assert category is not None, "Category seed missing from migrations"
        operator = Operator(
            id=uuid4(), legal_name="Example Test Operator", business_name="Test Operator",
            status="ACTIVE", created_at=now, updated_at=now,
        )
        vehicle = Vehicle(
            id=uuid4(), operator_id=operator.id, category_id=category.id,
            registration_number=f"TEST-{uuid4().hex[:12].upper()}",
            brand="Test", model="Sedan", city="Chennai", timezone="Asia/Kolkata",
            status="AVAILABLE", created_at=now, updated_at=now,
        )
        package = PricingPackage(
            id=uuid4(), operator_id=operator.id, name="One Day",
            service_type="SELF_DRIVE", duration_minutes=1440,
            included_km=Decimal("150"), base_price=Decimal("2000.00"),
            deposit=Decimal("4000.00"), currency="INR",
            tax_rate=Decimal("0.18"), active=True,
            created_at=now, updated_at=now,
        )
        db.add_all([operator, vehicle, package])
        quote_ids = []
        customer_ids = []
        for _ in range(2):
            user = User(
                id=uuid4(), email=f"race-{uuid4().hex}@example.test",
                password_hash="test-only-no-login", full_name="Test Customer",
                is_active=True, created_at=now, updated_at=now,
            )
            quote = Quote(
                id=uuid4(), customer_id=user.id, vehicle_id=vehicle.id,
                package_id=package.id, pickup_at=pickup, return_at=returned,
                pricing_version="fixed-package-v1", currency="INR",
                subtotal=Decimal("2000.00"), tax=Decimal("360.00"),
                discount=Decimal("0"), deposit=Decimal("4000.00"),
                total=Decimal("2360.00"), line_items={"package_units": 1},
                expires_at=now + timedelta(minutes=30),
                created_at=now, updated_at=now,
            )
            db.add_all([user, quote])
            db.add(RentalConfiguration(
                id=uuid4(), quote_id=quote.id, service_type="SELF_DRIVE",
                pickup_location="Chennai", return_location="Chennai",
                booking_timezone="Asia/Kolkata", details={},
            ))
            customer_ids.append(user.id)
            quote_ids.append(quote.id)
        vehicle_id = vehicle.id
        db.commit()

    gate = Barrier(2)
    def attempt(index: int) -> str:
        with SessionLocal() as db:
            quote = db.get(Quote, quote_ids[index])
            gate.wait(timeout=10)
            try:
                create_booking_from_quote(db, quote, customer_ids[index])
                db.commit()
                return "success"
            except ConflictError:
                db.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))

    assert sorted(results) == ["conflict", "success"]
    with SessionLocal() as db:
        count = db.scalar(
            select(func.count()).select_from(Booking).where(
                Booking.vehicle_id == vehicle_id
            )
        )
    assert count == 1
