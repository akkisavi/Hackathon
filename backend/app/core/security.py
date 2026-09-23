"""Password hashing, JWTs, API keys, reset tokens.

Passwords: bcrypt. API keys / reset tokens: SHA-256 of the secret (+ pepper
for API keys). Raw secrets are never stored.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
API_KEY_PREFIX = "sk_live_"


def get_password_hash(password: str) -> str:
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pw = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(pw, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: Any,
    token_version: int = 0,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta is not None
        else timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode = {"exp": expire, "sub": str(subject), "tv": int(token_version)}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def get_api_key_hash(api_key: str) -> str:
    settings = get_settings()
    return hashlib.sha256((api_key + settings.api_key_pepper).encode("utf-8")).hexdigest()


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def get_reset_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
