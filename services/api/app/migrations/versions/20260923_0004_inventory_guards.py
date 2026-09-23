"""rental configuration and buffered inventory reservations

Revision ID: 20260923_0004
Revises: 20260923_0003
"""
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260923_0004"
down_revision = "20260923_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "availability_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope_key", sa.String(120), nullable=False, unique=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operators.id")),
        sa.Column("pre_buffer_minutes", sa.Integer(), nullable=False),
        sa.Column("post_buffer_minutes", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "pre_buffer_minutes >= 0 AND post_buffer_minutes >= 0",
            name="ck_availability_policy_buffers",
        ),
    )
    policy_table = sa.table(
        "availability_policies",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("scope_key", sa.String()),
        sa.column("operator_id", postgresql.UUID(as_uuid=True)),
        sa.column("pre_buffer_minutes", sa.Integer()),
        sa.column("post_buffer_minutes", sa.Integer()),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        policy_table,
        [{
            "id": uuid5(NAMESPACE_URL, "pyro-rentals:availability-policy:GLOBAL"),
            "scope_key": "GLOBAL",
            "operator_id": None,
            "pre_buffer_minutes": 0,
            "post_buffer_minutes": 0,
            "updated_at": datetime.now(UTC),
        }],
    )

    op.create_table(
        "rental_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotes.id"), nullable=False, unique=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id"), unique=True),
        sa.Column("service_type", sa.String(60), nullable=False),
        sa.Column("pickup_location", sa.String(500), nullable=False),
        sa.Column("return_location", sa.String(500), nullable=False),
        sa.Column("booking_timezone", sa.String(64), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "ix_rental_configuration_service",
        "rental_configurations",
        ["service_type"],
    )

    op.create_table(
        "vehicle_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id"), nullable=False, unique=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_at > start_at", name="ck_vehicle_reservation_window"),
    )
    op.create_index(
        "ix_vehicle_reservation_lookup",
        "vehicle_reservations",
        ["vehicle_id", "status", "start_at", "end_at"],
    )
    op.execute(
        """ALTER TABLE vehicle_reservations
        ADD CONSTRAINT vehicle_reservations_no_overlap
        EXCLUDE USING gist (
          vehicle_id WITH =,
          tstzrange(start_at, end_at, '[)') WITH &&
        ) WHERE (status = 'ACTIVE')"""
    )


def downgrade() -> None:
    op.drop_table("vehicle_reservations")
    op.drop_table("rental_configurations")
    op.drop_table("availability_policies")
