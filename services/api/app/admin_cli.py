"""Development-only operator console for granting an admin role to a registered account.

Production admin provisioning must use an audited, out-of-band operations process.
"""
import argparse
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import AuditLog, Role, User, UserRole


def grant_development_admin(email: str, confirmed: bool) -> None:
    if get_settings().app_env not in {"development", "test"}:
        raise SystemExit("Admin bootstrap is restricted to development/test")
    if not confirmed:
        raise SystemExit("Add --confirm after reviewing the target email")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            raise SystemExit("Registered account not found")
        role = db.scalar(select(Role).where(Role.code == "SUPER_ADMIN"))
        if role is None:
            raise SystemExit("RBAC roles missing: run all migrations")

        if db.get(UserRole, (user.id, role.id)) is None:
            db.add(UserRole(user_id=user.id, role_id=role.id))
            db.add(AuditLog(
                id=uuid4(), actor_user_id=None,
                action="dev:admin-bootstrap", entity="user",
                entity_id=str(user.id), before_state=None,
                after_state={"role": "SUPER_ADMIN"},
                request_id="dev-cli", created_at=datetime.now(UTC),
            ))
            db.commit()
        print("Development admin permission granted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    grant_development_admin(args.email, args.confirm)
