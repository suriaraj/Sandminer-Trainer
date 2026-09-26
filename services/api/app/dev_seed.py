"""Explicit development-only deterministic demo catalog.

Run only after database migrations. Never use production data or credentials.
"""
import argparse
from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Operator, PricingPackage, Vehicle, VehicleCategory

CITIES = ["Chennai", "Bengaluru", "Hyderabad", "Coimbatore", "Puducherry"]
CATEGORIES = ["HATCHBACK", "SEDAN", "SUV", "MUV", "LUXURY"]
BRANDS = ["Maruti", "Hyundai", "Honda", "Toyota", "Tata"]
MODELS = ["Baleno", "Creta", "City", "Innova", "Nexon"]


def demo_id(kind: str, code: str):
    return uuid5(NAMESPACE_URL, "pyro-rentals:dev:" + kind + ":" + code)


def seed() -> None:
    if get_settings().app_env not in {"development", "test"}:
        raise SystemExit("Demo seeding is forbidden outside development/test")
    now = datetime.now(UTC)
    with SessionLocal() as db:
        categories = {
            row.code: row for row in db.scalars(
                select(VehicleCategory).where(VehicleCategory.code.in_(CATEGORIES))
            )
        }
        if len(categories) != len(CATEGORIES):
            raise SystemExit("Apply Alembic migrations before seeding catalog")
        for operator_index in range(20):
            operator_id = demo_id("operator", str(operator_index))
            operator = db.get(Operator, operator_id)
            if operator is None:
                operator = Operator(
                    id=operator_id,
                    legal_name=f"DEMO Rental Company {operator_index + 1}",
                    business_name=f"DEMO PYRO Fleet {operator_index + 1}",
                    status="ACTIVE",
                    created_at=now,
                    updated_at=now,
                )
                db.add(operator)
                db.flush()
            package_id = demo_id("package", str(operator_index))
            if db.get(PricingPackage, package_id) is None:
                db.add(PricingPackage(
                    id=package_id, operator_id=operator.id, name="24 h / 200 km (DEMO)",
                    service_type="SELF_DRIVE", duration_minutes=1440,
                    included_km=Decimal("200"),
                    base_price=Decimal("2500") + Decimal(operator_index * 50),
                    tax_rate=Decimal("0.18"), deposit=Decimal("5000"),
                    currency="INR", active=True,
                    created_at=now, updated_at=now,
                ))
            for j in range(5):
                vehicle_id = demo_id("vehicle", f"{operator_index}:{j}")
                if db.get(Vehicle, vehicle_id) is None:
                    category = categories[CATEGORIES[(operator_index+j) % 5]]
                    db.add(Vehicle(
                        id=vehicle_id, operator_id=operator_id,
                        category_id=category.id,
                        registration_number=f"DEMO-{operator_index:02d}-{j}",
                        brand=BRANDS[j], model=MODELS[j],
                        variant="DEVELOPMENT ONLY", city=CITIES[(operator_index+j) % 5],
                        timezone="Asia/Kolkata", status="AVAILABLE",
                        fuel="PETROL", transmission="AUTOMATIC" if j % 2 else "MANUAL",
                        seats=7 if j == 3 else 5,
                        created_at=now, updated_at=now,
                    ))
        db.commit()
    print("Seeded up to 20 fake operators and 100 fake vehicles.")


if __name__ == "__main__":
    argparse.ArgumentParser(description="Development fake catalog seed").parse_args()
    seed()
