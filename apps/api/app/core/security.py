"""Security helpers for password hashing and auth tokens."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}:{base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        salt_b64, digest_b64 = encoded_hash.split(":", maxsplit=1)
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
    except (ValueError, TypeError):
        return False
    current = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(expected, current)


def build_access_token(*, user_id: str, secret: str, ttl_seconds: int) -> str:
    exp = int(time.time()) + ttl_seconds
    payload = f"{user_id}:{exp}"
    sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def parse_access_token(*, token: str, secret: str) -> str | None:
    try:
        user_id, exp_s, sig = token.split(":", maxsplit=2)
        exp = int(exp_s)
    except (ValueError, TypeError):
        return None
    payload = f"{user_id}:{exp}"
    expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    if exp < int(time.time()):
        return None
    return user_id


def hash_email_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
