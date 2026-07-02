"""
Authentication: password hashing and JWT issuance/verification.
Uses OAuth2 password bearer flow.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User
from app.db.session import get_db_session

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_ROOT_PATH}/auth/token", auto_error=False
)


def _password_bytes(password: str) -> bytes:
    raw = password.encode("utf-8")
    if len(raw) <= 72:
        return raw
    return hashlib.sha256(raw).hexdigest().encode("ascii")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, role: str = "analyst") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def seed_default_user() -> None:
    """Create a default user on startup if none exist.

    Keeps the API usable out of the box when AUTH_REQUIRED is on. Controlled by
    SEED_DEFAULT_USER and the DEFAULT_ADMIN_* settings.
    """
    if not settings.SEED_DEFAULT_USER:
        return
    if not settings.DEFAULT_ADMIN_PASSWORD.strip():
        logger.info("Default user seeding skipped; DEFAULT_ADMIN_PASSWORD is not configured")
        return
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return
        db.add(
            User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                role=settings.DEFAULT_ADMIN_ROLE,
            )
        )
        db.commit()
        logger.info("Seeded default user '%s'", settings.DEFAULT_ADMIN_USERNAME)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Default user seeding skipped: %s", exc)
        db.rollback()
    finally:
        db.close()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session),
) -> Optional[User]:
    """Resolve the current user. When AUTH_REQUIRED is false, allow anonymous."""
    if not settings.AUTH_REQUIRED:
        return None

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exc
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exc
    except JWTError as exc:
        logger.debug(f"JWT decode failed: {exc}")
        raise credentials_exc from exc

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exc
    request.state.user = user
    return user
