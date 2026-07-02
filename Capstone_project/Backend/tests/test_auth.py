"""Auth unit tests (hashing + JWT)."""

from jose import jwt as jose_jwt

from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import settings


def test_password_hash_roundtrip():
    hashed = hash_password("super-secret-pw")
    assert hashed != "super-secret-pw"
    assert verify_password("super-secret-pw", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_encodes_subject_and_role():
    token = create_access_token(subject="alice", role="reviewer")
    decoded = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == "alice"
    assert decoded["role"] == "reviewer"
    assert "exp" in decoded
