import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_models import AuthSession
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(
    db: Session,
    user_id: UUID,
    device_label: str | None,
) -> tuple[str, str, AuthSession]:
    settings = get_settings()
    now = datetime.now(UTC)
    session_id = uuid4()
    access = create_access_token(user_id, session_id)
    refresh = create_refresh_token(user_id, session_id)
    session = AuthSession(
        id=session_id,
        user_id=user_id,
        refresh_token_hash=token_hash(refresh),
        device_label=(device_label or "").strip()[:200] or None,
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_days),
    )
    db.add(session)
    return access, refresh, session


def rotate_session(db: Session, refresh_token: str) -> tuple[str, str, AuthSession]:
    user_id, session_id = decode_refresh_token(refresh_token)
    session = db.get(AuthSession, session_id)
    now = datetime.now(UTC)
    if (
        session is None
        or session.user_id != user_id
        or session.revoked_at is not None
        or session.expires_at <= now
        or session.refresh_token_hash != token_hash(refresh_token)
    ):
        raise HTTPException(status_code=401, detail="Refresh session is invalid")

    access = create_access_token(user_id, session.id)
    refresh = create_refresh_token(user_id, session.id)
    session.refresh_token_hash = token_hash(refresh)
    session.last_used_at = now
    session.expires_at = now + timedelta(days=get_settings().refresh_token_days)
    return access, refresh, session


def revoke_session(db: Session, user_id: UUID, session_id: UUID) -> bool:
    session = db.get(AuthSession, session_id)
    if session is None or session.user_id != user_id:
        return False
    if session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
    return True


def revoke_all_sessions(db: Session, user_id: UUID) -> int:
    now = datetime.now(UTC)
    sessions = db.scalars(
        select(AuthSession).where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
    ).all()
    for session in sessions:
        session.revoked_at = now
    return len(sessions)
