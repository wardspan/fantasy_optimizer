from __future__ import annotations

from typing import Dict, List
from sqlmodel import Session

from .vorp import compute_vorp


def evaluate_trade(session: Session, week: int, players_in: List[int], players_out: List[int]) -> Dict:
    vorp = compute_vorp(session, week)
    delta_my = sum(vorp.get(pid, 0.0) for pid in players_in) - sum(vorp.get(pid, 0.0) for pid in players_out)
    delta_their = -delta_my
    # Fairness score 0-100: 100 when deltas are equal/opposite close to zero
    fairness = max(0.0, 100.0 - abs(delta_my - (-delta_their)) * 10.0)
    rationale = f"My VORP change {round(delta_my,2)}, theirs {round(delta_their,2)}. Balanced if near 0."
    return {"fairness": round(fairness, 1), "delta_my": round(delta_my, 2), "delta_their": round(delta_their, 2), "rationale": rationale}

