from __future__ import annotations

from typing import Dict, List
from sqlmodel import Session, select

from ..models import Player, Projection, Roster, RosterStatus
from .vorp import compute_vorp


def waiver_suggestions(session: Session, week: int) -> List[Dict]:
    vorp = compute_vorp(session, week)
    # My rostered vs free agents
    rosters = session.exec(select(Roster)).all()
    my_players = {r.player_id for r in rosters if r.my_team and r.status in (RosterStatus.start, RosterStatus.bench)}
    fa_players = {r.player_id for r in rosters if r.status == RosterStatus.fa}

    # Worst rostered per position
    pos_to_rostered: Dict[str, List[int]] = {}
    pos_to_fa: Dict[str, List[int]] = {}
    for pid in my_players:
        p = session.get(Player, pid)
        pos_to_rostered.setdefault(p.position, []).append(pid)
    for pid in fa_players:
        p = session.get(Player, pid)
        pos_to_fa.setdefault(p.position, []).append(pid)

    recs: List[Dict] = []
    for pos, fa_ids in pos_to_fa.items():
        rostered_ids = pos_to_rostered.get(pos, [])
        worst_vorp = min((vorp.get(pid, 0.0) for pid in rostered_ids), default=0.0)
        # Top FA by VORP delta
        for pid in sorted(fa_ids, key=lambda i: vorp.get(i, 0.0), reverse=True)[:5]:
            delta = vorp.get(pid, 0.0) - worst_vorp
            if delta <= 0:
                continue
            p = session.get(Player, pid)
            # Simple FAAB heuristic: map delta to 1-20 range with bounds and late-season decay placeholder
            faab = max(1, min(20, int(delta)))
            recs.append({
                "player_id": pid,
                "name": p.name,
                "position": p.position,
                "vorp_delta": round(delta, 2),
                "faab_bid": faab,
                "rationale": f"Improves {pos} by {round(delta,2)} VORP; schedule-adjusted."
            })
    return sorted(recs, key=lambda r: r["vorp_delta"], reverse=True)

