from __future__ import annotations

"""
Yahoo Fantasy Sports provider (scaffold).

Yahoo's official API requires OAuth 1.0a and user authorization. This file defines
placeholders that return 0 when credentials are not configured. Replace with a
real implementation when OAuth creds are available, or wire an internal proxy.
"""

from sqlmodel import Session
from backend.app.settings import get_settings


def fetch_projections(session: Session, week: int) -> int:
    settings = get_settings()
    if not (settings.yahoo_client_id and settings.yahoo_secret):
        return 0
    # TODO: Implement via Yahoo Fantasy Sports API (OAuth required).
    # Strategy: use stored OAuth tokens to call players/stats or projections for the given week.
    # Until tokens are configured and endpoints mapped, return 0.
    return 0


def fetch_adp(session: Session) -> int:
    settings = get_settings()
    if not (settings.yahoo_client_id and settings.yahoo_secret):
        return 0
    # TODO: Optionally implement ADP-like metrics from Yahoo if available.
    return 0
