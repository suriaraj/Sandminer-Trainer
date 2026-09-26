"""Add bounded payment holds and package-scoped service pricing.

Revision ID: 20260926_0005
Revises: 20260923_0004
"""
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260926_0005"
down_revision = "20260923_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("payment_deadline_at", sa.DateTime(timezone=True)))
    op.add_column("vehicle_reservations", sa.Column("expires_at", sa.DateTime(timezone=True)))
    op.add_column(
        "pricing_packages",
        sa.Column("service_type", sa.String(60), server_default="SELF_DRIVE", nullable=False),
    )
    op.create_index(
        "ix_booking_deadline_status", "bookings",
        ["status", "payment_deadline_at"],
    )
    categories = sa.table(
        "vehicle_categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("active", sa.Boolean()),
    )
    codes = ["HATCHBACK", "SEDAN", "SUV", "MUV", "LUXURY"]
    op.bulk_insert(categories, [
        {
            "id": uuid5(NAMESPACE_URL, "pyro-rentals:category:" + code),
            "code": code,
            "name": code.title(),
            "active": True,
        }
        for code in codes
    ])


def downgrade() -> None:
    op.drop_index("ix_booking_deadline_status", table_name="bookings")
    op.drop_column("pricing_packages", "service_type")
    op.drop_column("vehicle_reservations", "expires_at")
    op.drop_column("bookings", "payment_deadline_at")
    # Seed categories are kept because vehicles may reference them.
