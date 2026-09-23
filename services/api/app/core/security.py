from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_models import AuthSession
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Permission, RolePermission, User, UserRole


_hasher = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except Exception:
        return False


def _encode(
    user_id: UUID,
    session_id: UUID,
    token_type: str,
    secret: str,
    lifetime: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": str(uuid4()),
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_access_token(user_id: UUID, session_id: UUID) -> str:
    settings = get_settings()
    return _encode(
        user_id,
        session_id,
        "access",
        settings.jwt_secret,
        timedelta(minutes=settings.access_token_minutes),
    )


def create_refresh_token(user_id: UUID, session_id: UUID) -> str:
    settings = get_settings()
    return _encode(
        user_id,
        session_id,
        "refresh",
        settings.jwt_refresh_secret,
        timedelta(days=settings.refresh_token_days),
    )


def _decode(token: str, secret: str, expected_type: str) -> tuple[UUID, UUID]:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get("typ") != expected_type:
            raise ValueError("wrong token type")
        return UUID(payload["sub"]), UUID(payload["sid"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid {expected_type} token",
        ) from exc


def decode_access_token(token: str) -> tuple[UUID, UUID]:
    return _decode(token, get_settings().jwt_secret, "access")


def decode_refresh_token(token: str) -> tuple[UUID, UUID]:
    return _decode(token, get_settings().jwt_refresh_secret, "refresh")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id, session_id = decode_access_token(credentials.credentials)
    session = db.get(AuthSession, session_id)
    now = datetime.now(UTC)
    if (
        session is None
        or session.user_id != user_id
        or session.revoked_at is not None
        or session.expires_at <= now
    ):
        raise HTTPException(status_code=401, detail="Session is no longer active")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def permission_codes(db: Session, user_id: UUID) -> set[str]:
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
    )
    return set(db.scalars(stmt).all())


def require_permissions(*required: str):
    def dependency(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        granted = permission_codes(db, user.id)
        if not set(required).issubset(granted):
            raise HTTPException(status_code=403, detail="Missing required permission")
        return user

    return dependency
