from __future__ import annotations

from typing import Iterable
import re
from sqlmodel import Session, select
from sqlalchemy import func
from backend.app.models import Player, Projection, Injury, ADP


def _normalize_name(name: str) -> str:
    s = name.strip().lower()
    # unify quotes/dashes and collapse spaces
    for ch in ["’", "‘", "`", "´", "–", "—"]:
        s = s.replace(ch, "'")
    # strip trailing team abbreviations or dst
    s = re.sub(r"\s+(?:[a-z]{2,3}|d\/st|dst)$", "", s)
    # drop common suffixes like jr, sr, ii, iii
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\.?$", "", s)
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def get_or_create_player(session: Session, name: str, position: str | None = None, team: str | None = None) -> Player:
    # Try exact, then case-insensitive match to avoid duplicates from minor formatting diffs
    p = session.exec(select(Player).where(Player.name == name)).first()
    if not p:
        p = session.exec(select(Player).where(func.lower(Player.name) == _normalize_name(name))).first()
    if not p:
        p = Player(name=name, position=(position or "FLEX"), team=team)
        session.add(p)
        session.flush()
    else:
        # Update missing fields if available
        if position and (not p.position or p.position == "FLEX"):
            p.position = position
        if team and not p.team:
            p.team = team
    return p


def upsert_projection(session: Session, player: Player, week: int, source: str, expected: float, stdev: float | None = None) -> None:
    row = session.exec(select(Projection).where(Projection.player_id == player.id, Projection.week == week, Projection.source == source)).first()
    if not row:
        row = Projection(player_id=player.id, week=week, source=source, expected=expected, stdev=stdev)
        session.add(row)
    else:
        row.expected = expected
        row.stdev = stdev


def upsert_injury(session: Session, player: Player, week: int, status: str, note: str | None = None) -> None:
    row = session.exec(select(Injury).where(Injury.player_id == player.id, Injury.week == week)).first()
    if not row:
        row = Injury(player_id=player.id, week=week, status=status, note=note)
        session.add(row)
    else:
        row.status = status
        row.note = note


def upsert_adp(session: Session, player: Player, source: str, rank: float) -> None:
    row = session.exec(select(ADP).where(ADP.player_id == player.id, ADP.source == source)).first()
    if not row:
        row = ADP(player_id=player.id, source=source, rank=rank)
        session.add(row)
    else:
        row.rank = rank
