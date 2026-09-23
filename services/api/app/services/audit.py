from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AuditLog


def append_audit(
    db: Session,
    *,
    actor_user_id: UUID | None,
    action: str,
    entity: str,
    entity_id: str,
    request_id: str | None,
    before_state: dict | None = None,
    after_state: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            request_id=request_id,
            created_at=datetime.now(UTC),
        )
    )
