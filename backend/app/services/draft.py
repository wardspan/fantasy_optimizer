from __future__ import annotations

from typing import Dict, List, Set
from sqlmodel import Session, select

from ..models import Player, ADP
from .vorp import compute_vorp


def _normalize_name(name: str) -> str:
    s = name.strip().lower()
    for ch in ["’", "‘", "`", "´", "–", "—"]:
        s = s.replace(ch, "'")
    # strip trailing team abbreviations or dst
    import re as _re
    s = _re.sub(r"\s+(?:[a-z]{2,3}|d\/st|dst)$", "", s)
    s = _re.sub(r"\b(jr|sr|ii|iii|iv|v)\.?$", "", s)
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def best_picks_by_position(session: Session, round_num: int, pick: int) -> Dict[str, List[Dict]]:
    # Use VORP blended with ADP reach
    vorp = compute_vorp(session, week=1)  # use week 1 as default for demo
    adps = session.exec(select(ADP)).all()
    adp_fp: Dict[int, float] = {}
    adp_espn: Dict[int, float] = {}
    for a in adps:
        src = (a.source or "").lower()
        if src.startswith("fantasypros") or src == "fp":
            adp_fp[a.player_id] = a.rank
        elif src.startswith("espn"):
            adp_espn[a.player_id] = a.rank
    results: Dict[str, List[Dict]] = {}
    seen: Set[str] = set()
    for player in session.exec(select(Player)).all():
        key = _normalize_name(player.name)
        if key in seen:
            continue
        seen.add(key)
        v = vorp.get(player.id, 0.0)
        # Prefer ESPN ADP for reach if available, else FP
        adp_es = adp_espn.get(player.id)
        adp_fp_val = adp_fp.get(player.id)
        adp_for_reach = adp_es if adp_es is not None else (adp_fp_val if adp_fp_val is not None else 999)
        reach = max(0, (int(adp_for_reach) // 10))
        # crude reach indicator vs current round
        reach = max(0, round_num - reach)
        score = v - 0.1 * reach
        results.setdefault(player.position, []).append({
            "player_id": player.id,
            "name": player.name,
            "team": player.team,
            "score": round(score, 2),
            "vorp": round(v, 2),
            "adp_fp": adp_fp_val if adp_fp_val is not None else None,
            "adp_espn": adp_es if adp_es is not None else None,
            "reach": reach,
            "rationale": f"VORP {round(v,2)}; ADP FP={adp_fp_val if adp_fp_val is not None else 'N/A'}, ESPN={adp_es if adp_es is not None else 'N/A'}."
        })
    for pos in results:
        results[pos] = sorted(results[pos], key=lambda r: r["score"], reverse=True)[:10]
    return results
