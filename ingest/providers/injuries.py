from __future__ import annotations

from sqlmodel import Session, select
from backend.app.models import Player
from ..util import upsert_injury


def fetch_injuries(session: Session, week: int) -> int:
    count = 0
    for p in session.exec(select(Player)).all():
        upsert_injury(session, p, week, "Active")
        count += 1
    return count

