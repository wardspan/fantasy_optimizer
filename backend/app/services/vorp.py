from __future__ import annotations

from typing import Dict, List, Tuple
from sqlmodel import Session, select

from ..models import Player, Projection, Roster, RosterStatus


REPLACEMENT_INDEX = {"QB": 12, "RB": 24, "WR": 24, "TE": 12, "K": 12, "DST": 12}


def compute_replacement_levels(session: Session, week: int) -> Dict[str, float]:
    # Use free-agent pool or league baseline: simplest approach: sort all projections by position
    stmt = select(Projection, Player).join(Player, Projection.player_id == Player.id).where(Projection.week == week)
    rows = session.exec(stmt).all()
    pos_points: Dict[str, List[float]] = {}
    for proj, player in rows:
        pos_points.setdefault(player.position, []).append(proj.expected)
    replacement: Dict[str, float] = {}
    for pos, pts in pos_points.items():
        idx = REPLACEMENT_INDEX.get(pos, 12)
        pts_sorted = sorted(pts, reverse=True)
        if len(pts_sorted) >= idx:
            replacement[pos] = pts_sorted[idx - 1]
        else:
            replacement[pos] = pts_sorted[-1] if pts_sorted else 0.0
    return replacement


def compute_vorp(session: Session, week: int) -> Dict[int, float]:
    repl = compute_replacement_levels(session, week)
    stmt = select(Projection, Player).join(Player, Projection.player_id == Player.id).where(Projection.week == week)
    rows = session.exec(stmt).all()
    vorp: Dict[int, float] = {}
    for proj, player in rows:
        base = repl.get(player.position, 0.0)
        vorp[player.id] = proj.expected - base
    return vorp

