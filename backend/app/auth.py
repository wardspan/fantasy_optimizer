from __future__ import annotations

import time
from typing import Optional
import hmac
import hashlib
import base64

from fastapi import Depends, HTTPException, Header

from .settings import get_settings


def _sign(payload: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def create_token(sub: str, exp_seconds: int = 7 * 24 * 3600) -> str:
    settings = get_settings()
    exp = int(time.time()) + exp_seconds
    payload = f"sub={sub}&exp={exp}"
    sig = _sign(payload, settings.auth_secret)
    token = f"v1.{base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')}.{sig}"
    return token


def verify_token(token: str) -> bool:
    try:
        if not token.startswith("v1."):
            return False
        _ver, b64payload, sig = token.split(".", 2)
        payload = base64.urlsafe_b64decode(b64payload + "==").decode()
        expected = _sign(payload, get_settings().auth_secret)
        if not hmac.compare_digest(expected, sig):
            return False
        parts = dict(pair.split("=", 1) for pair in payload.split("&"))
        if int(parts.get("exp", "0")) < int(time.time()):
            return False
        return True
    except Exception:
        return False


def auth_required(authorization: Optional[str] = Header(default=None)):
    settings = get_settings()
    # If no password configured, auth not required
    if not settings.app_password:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.split(" ", 1)[1]
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")

