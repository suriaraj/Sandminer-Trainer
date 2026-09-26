import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.models import IdempotencyKey


def payload_hash(payload: dict) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def begin_idempotent(db: Session, scope: str, key: str, payload: dict) -> IdempotencyKey:
    digest = payload_hash(payload)
    existing = db.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.scope == scope,
            IdempotencyKey.key == key,
        )
    )
    if existing:
        if existing.request_hash != digest:
            raise ConflictError(
                "IDEMPOTENCY_KEY_REUSED",
                "Idempotency key was reused with a different payload",
            )
        return existing

    record = IdempotencyKey(
        scope=scope,
        key=key,
        request_hash=digest,
        created_at=datetime.now(UTC),
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "IDEMPOTENCY_IN_PROGRESS",
            "Another request with this idempotency key is already in progress",
        ) from exc
    return record
