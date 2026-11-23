"""Argon2 password hashing and short-lived signed access tokens."""

from datetime import datetime, timedelta, timezone
import logging
import os
import secrets
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import UserAccount

logger = logging.getLogger(__name__)
ACCESS_TOKEN_SECONDS = 60 * 60
JWT_ISSUER = "skillpulse-ai"
JWT_ALGORITHM = "HS256"
_configured_secret = os.environ.get("SKILLPULSE_JWT_SECRET")
if not _configured_secret and os.environ.get("SKILLPULSE_ENVIRONMENT", "demo").casefold() == "production":
    raise RuntimeError("SKILLPULSE_JWT_SECRET must be configured in production")
JWT_SECRET = _configured_secret or secrets.token_urlsafe(48)
if not _configured_secret:
    logger.warning("No SKILLPULSE_JWT_SECRET set; using a temporary development key. Existing tokens expire on restart.")

password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-skillpulse-password")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hash.verify(password, stored_hash)


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(seconds=ACCESS_TOKEN_SECONDS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserAccount:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sign in to access this resource",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except InvalidTokenError:
        raise unauthorized from None
    user = db.get(UserAccount, payload.get("sub"))
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_roles(*allowed_roles: str) -> Callable:
    def role_dependency(user: UserAccount = Depends(current_user)) -> UserAccount:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot access this resource")
        return user

    return role_dependency
