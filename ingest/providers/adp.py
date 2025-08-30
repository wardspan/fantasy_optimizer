from __future__ import annotations

from sqlmodel import Session
from .fantasypros import fetch_adp_fantasypros


def fetch_adp(session: Session) -> int:
    # Prefer FantasyPros ADP (public) for now
    return fetch_adp_fantasypros(session)
