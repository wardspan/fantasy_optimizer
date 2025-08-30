from __future__ import annotations

from collections import defaultdict
from typing import Dict, List
from sqlmodel import Session, select

from ..models import Projection, Player, SettingsRow


DEFAULT_WEIGHTS = {
    "QB": {"espn": 0.5, "fantasypros": 0.3, "sportsdata": 0.2, "yahoo": 0.0},
    "RB": {"espn": 0.5, "fantasypros": 0.3, "sportsdata": 0.2, "yahoo": 0.0},
    "WR": {"espn": 0.5, "fantasypros": 0.3, "sportsdata": 0.2, "yahoo": 0.0},
    "TE": {"espn": 0.5, "fantasypros": 0.3, "sportsdata": 0.2, "yahoo": 0.0},
    "K":  {"espn": 0.5, "fantasypros": 0.3, "sportsdata": 0.2, "yahoo": 0.0},
    "DST": {"espn": 0.5, "fantasypros": 0.3, "sportsdata": 0.2, "yahoo": 0.0},
}


def get_weights(session: Session) -> Dict[str, Dict[str, float]]:
    settings = session.get(SettingsRow, 1)
    if not settings or "weights" not in settings.data:
        return DEFAULT_WEIGHTS
    return settings.data.get("weights", DEFAULT_WEIGHTS)


def blend_projections(session: Session, week: int) -> Dict[int, Dict[str, float]]:
    stmt = select(Projection, Player).join(Player, Projection.player_id == Player.id).where(Projection.week == week)
    rows = session.exec(stmt).all()
    by_player: Dict[int, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    positions: Dict[int, str] = {}
    for proj, player in rows:
        positions[player.id] = player.position
        by_player[player.id][proj.source].append(proj.expected)

    weights = get_weights(session)
    blended: Dict[int, Dict[str, float]] = {}
    for pid, src_map in by_player.items():
        pos = positions.get(pid, "FLEX")
        pos_weights = weights.get(pos, {"espn": 0.6, "fantasypros": 0.4})
        # Weighted mean over available sources; allow exclusion if missing
        total_w = 0.0
        total = 0.0
        for src, vals in src_map.items():
            if src not in pos_weights:
                continue
            w = pos_weights[src]
            avg = sum(vals) / len(vals)
            total_w += w
            total += w * avg
        if total_w == 0:
            continue
        blended[pid] = {"expected": total / total_w}
    return blended
