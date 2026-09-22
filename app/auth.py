import hashlib
import hmac
import secrets
import time

from app.config import settings

TOKEN_TTL_SECONDS = 30 * 24 * 3600


def _secret() -> bytes:
    if settings.secret_key:
        return settings.secret_key.encode()
    return b"reader-insecure-dev-secret"


def make_token(username: str) -> str:
    expiry = int(time.time()) + TOKEN_TTL_SECONDS
    payload = f"{username}|{expiry}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_token(token: str) -> bool:
    try:
        payload, sig = token.rsplit(".", 1)
        expected = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        _username, expiry = payload.split("|")
        return int(expiry) > time.time()
    except (ValueError, TypeError):
        return False


def check_credentials(username: str, password: str) -> bool:
    if not settings.auth_enabled:
        return True
    return secrets.compare_digest(username, settings.auth_username) and secrets.compare_digest(
        password, settings.auth_password
    )
