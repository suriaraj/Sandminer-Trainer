"""rental lifecycle and baseline RBAC

Revision ID: 20260923_0002
Revises: 20260923_0001
"""
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260923_0002"
down_revision = "20260923_0001"
branch_labels = None
depends_on = None


ROLES = [
    "CUSTOMER", "DRIVER", "OPERATOR_OWNER", "OPERATOR_MANAGER", "OPERATOR_STAFF",
    "INSPECTION_AGENT", "FINANCE_ADMIN", "OPERATIONS_ADMIN", "SUPPORT_AGENT",
    "MARKETING_ADMIN", "SUPER_ADMIN", "ANALYST", "SYSTEM",
]
PERMISSIONS = [
    "vehicle:create", "vehicle:read", "vehicle:update", "vehicle:delete",
    "booking:create", "booking:read", "booking:update", "booking:cancel",
    "payment:read", "payment:refund", "operator:approve", "kyc:approve",
    "pricing:update", "settlement:approve", "admin:users", "admin:settings",
    "handover:create", "inspection:create", "damage:create", "support:manage",
]
ROLE_MAP = {
    "CUSTOMER": {"vehicle:read", "booking:create", "booking:read"},
    "DRIVER": {"booking:read", "handover:create"},
    "OPERATOR_OWNER": {
        "vehicle:create", "vehicle:read", "vehicle:update", "booking:read",
        "booking:update", "pricing:update", "handover:create", "inspection:create",
        "damage:create",
    },
    "OPERATOR_MANAGER": {
        "vehicle:create", "vehicle:read", "vehicle:update", "booking:read",
        "booking:update", "pricing:update", "handover:create", "inspection:create",
        "damage:create",
    },
    "OPERATOR_STAFF": {
        "vehicle:read", "booking:read", "booking:update", "handover:create"
    },
    "INSPECTION_AGENT": {
        "vehicle:read", "booking:read", "inspection:create", "damage:create"
    },
    "FINANCE_ADMIN": {
        "booking:read", "payment:read", "payment:refund", "settlement:approve"
    },
    "OPERATIONS_ADMIN": {
        "vehicle:read", "vehicle:update", "booking:read", "booking:update",
        "booking:cancel", "operator:approve", "kyc:approve", "handover:create",
        "inspection:create", "damage:create",
    },
    "SUPPORT_AGENT": {"booking:read", "support:manage"},
    "MARKETING_ADMIN": {"vehicle:read"},
    "ANALYST": {"vehicle:read", "booking:read", "payment:read"},
}
ROLE_MAP["SUPER_ADMIN"] = set(PERMISSIONS)
ROLE_MAP["SYSTEM"] = set(PERMISSIONS)


def stable_id(kind: str, code: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"pyro-rentals:{kind}:{code}"))


def upgrade() -> None:
    role_table = sa.table(
        "roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
    )
    permission_table = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
    )
    role_permission_table = sa.table(
        "role_permissions",
        sa.column("role_id", postgresql.UUID(as_uuid=True)),
        sa.column("permission_id", postgresql.UUID(as_uuid=True)),
    )
    op.bulk_insert(
        role_table,
        [{"id": stable_id("role", code), "code": code} for code in ROLES],
    )
    op.bulk_insert(
        permission_table,
        [{"id": stable_id("permission", code), "code": code} for code in PERMISSIONS],
    )
    rows = []
    for role, permissions in ROLE_MAP.items():
        for permission in permissions:
            rows.append(
                {
                    "role_id": stable_id("role", role),
                    "permission_id": stable_id("permission", permission),
                }
            )
    op.bulk_insert(role_permission_table, rows)

    op.create_table(
        "kyc_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("service_type", sa.String(60), nullable=False),
        sa.Column("provider", sa.String(80)),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("reason", sa.String(500)),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kyc_customer_status", "kyc_cases", ["customer_id", "status"])
    op.create_table(
        "kyc_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kyc_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kyc_cases.id"), nullable=False),
        sa.Column("document_type", sa.String(80), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "deposits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id"), nullable=False, unique=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("provider_reference", sa.String(160)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "deposit_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deposit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deposits.id"), nullable=False),
        sa.Column("transaction_type", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("reference", sa.String(160), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_deposit_tx_amount"),
    )
    op.create_table(
        "handover_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id"), nullable=False, unique=True),
        sa.Column("odometer", sa.Numeric(12, 1), nullable=False),
        sa.Column("fuel_level_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("condition", postgresql.JSONB(), nullable=False),
        sa.Column("accessories", postgresql.JSONB(), nullable=False),
        sa.Column("acknowledgement_method", sa.String(40), nullable=False),
        sa.Column("acknowledged_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("fuel_level_percent >= 0 AND fuel_level_percent <= 100", name="ck_handover_fuel"),
    )
    op.create_table(
        "inspection_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id"), nullable=False, unique=True),
        sa.Column("odometer", sa.Numeric(12, 1), nullable=False),
        sa.Column("fuel_level_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("condition", postgresql.JSONB(), nullable=False),
        sa.Column("accessories", postgresql.JSONB(), nullable=False),
        sa.Column("additional_km", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("late_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("fuel_level_percent >= 0 AND fuel_level_percent <= 100", name="ck_inspection_fuel"),
        sa.CheckConstraint("additional_km >= 0 AND late_minutes >= 0", name="ck_inspection_usage"),
    )
    op.create_table(
        "damage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("location", sa.String(160), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("severity", sa.String(40), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("approved_cost", sa.Numeric(14, 2)),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("estimated_cost >= 0 AND (approved_cost IS NULL OR approved_cost >= 0)", name="ck_damage_cost"),
    )
    op.create_table(
        "settlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id"), nullable=False, unique=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operators.id"), nullable=False),
        sa.Column("gross_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("platform_commission", sa.Numeric(14, 2), nullable=False),
        sa.Column("taxes", sa.Numeric(14, 2), nullable=False),
        sa.Column("adjustments", sa.Numeric(14, 2), nullable=False),
        sa.Column("refunds", sa.Numeric(14, 2), nullable=False),
        sa.Column("net_payable", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ledger_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reference_type", sa.String(60), nullable=False),
        sa.Column("reference_id", sa.String(80), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ledger_transactions.id"), nullable=False),
        sa.Column("account_code", sa.String(120), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("direction IN ('DEBIT','CREDIT') AND amount >= 0", name="ck_ledger_entry"),
    )
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("overall_rating", sa.Integer(), nullable=False),
        sa.Column("vehicle_rating", sa.Integer()),
        sa.Column("operator_rating", sa.Integer()),
        sa.Column("driver_rating", sa.Integer()),
        sa.Column("comment", sa.String(2000)),
        sa.Column("moderation_status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("booking_id", "customer_id", name="uq_review_booking_customer"),
        sa.CheckConstraint("overall_rating BETWEEN 1 AND 5", name="ck_review_overall"),
    )
    op.create_table(
        "support_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id")),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(240), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for table in [
        "notifications", "support_tickets", "reviews", "ledger_entries",
        "ledger_transactions", "settlements", "damage_records", "inspection_records",
        "handover_records", "deposit_transactions", "deposits", "kyc_documents", "kyc_cases",
    ]:
        op.drop_table(table)
    op.execute("DELETE FROM role_permissions")
    op.execute("DELETE FROM permissions")
    op.execute("DELETE FROM roles")
