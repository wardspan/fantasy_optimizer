from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
from sqlmodel import Session, select
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, PULP_CBC_CMD, LpStatus

from ..models import Player, Projection, Roster, RosterStatus, Injury, Game


LINEUP_SLOTS = [
    ("QB", 1),
    ("RB", 2),
    ("WR", 2),
    ("TE", 1),
    ("FLEX", 1),
    ("K", 1),
    ("DST", 1),
]

FLEX_POS = {"RB", "WR", "TE"}


def _risk_adjust(expected: float, stdev: float | None, lam: float) -> float:
    s = stdev if stdev is not None else 0.0
    return expected - lam * s


def _injury_penalty(status: str | None) -> float:
    if not status:
        return 0.0
    status = status.lower()
    if status in ("out",):
        return -8.0
    if status in ("doubtful",):
        return -4.0
    if status in ("questionable",):
        return -2.0
    return 0.0


def get_candidates(session: Session, week: int) -> List[Tuple[Player, Projection, float]]:
    # Consider only my roster (not free agents) for lineup
    stmt = (
        select(Projection, Player, Roster)
        .join(Player, Projection.player_id == Player.id)
        .join(Roster, Roster.player_id == Player.id)
        .where(
            Projection.week == week,
            Roster.my_team == True,
            Roster.status.in_([RosterStatus.start, RosterStatus.bench, RosterStatus.ir]),
        )
    )
    rows = session.exec(stmt).all()
    # Injuries map for this week
    inj_rows = session.exec(select(Injury).where(Injury.week == week)).all()
    inj_map = {r.player_id: r.status for r in inj_rows}
    candidates: List[Tuple[Player, Projection, float]] = []
    for proj, player, _roster in rows:
        penalty = _injury_penalty(inj_map.get(player.id))
        candidates.append((player, proj, penalty))
    return candidates


def optimize_lineup(session: Session, week: int, objective: str = "risk", lam: float = 0.35, stack_bonus: bool = False) -> Dict:
    cands = get_candidates(session, week)
    # Build injury map for badges
    inj_rows = session.exec(select(Injury).where(Injury.week == week)).all()
    inj_map = {r.player_id: r.status for r in inj_rows}
    # Decision vars per player for each eligible slot
    prob = LpProblem("lineup", LpMaximize)

    # Build slot requirements
    slot_reqs: List[Tuple[str, int]] = LINEUP_SLOTS

    # Vars: x_{player,slot}
    x: Dict[Tuple[int, str], LpVariable] = {}
    values: Dict[int, float] = {}

    for player, proj, penalty in cands:
        expected = proj.expected
        stdev = proj.stdev or 0.0
        val = expected if objective == "expected" else _risk_adjust(expected, stdev, lam)
        val += penalty
        values[player.id] = val
        # Eligible slots
        elig = {player.position}
        if player.position in FLEX_POS:
            elig.add("FLEX")
        for slot, _ in slot_reqs:
            if slot in elig:
                x[(player.id, slot)] = LpVariable(f"x_{player.id}_{slot}", lowBound=0, upBound=1, cat="Binary")

    # Objective: sum(values * x) + optional simple stack bonus (QB+WR same team)
    objective_terms = []
    objective_terms += [values[pid] * var for (pid, _slot), var in x.items()]
    # Stack bonus approximation: if QB and WR from same team both selected, add small bonus
    if stack_bonus:
        qbs = [(p.id, p.team) for p, _pr, _pn in cands if p.position == "QB"]
        wrs = [(p.id, p.team) for p, _pr, _pn in cands if p.position == "WR"]
        # Use product linearization: add for each pair a small bonus when both are chosen in any slot
        bonus = 0.5
        for qid, team_q in qbs:
            for wid, team_w in wrs:
                if team_q and team_q == team_w:
                    # Approximate by distributing bonus across their vars
                    objective_terms += [bonus * x[(qid, "QB")]] if (qid, "QB") in x else []
                    # WR could be WR or FLEX
                    if (wid, "WR") in x:
                        objective_terms += [bonus * x[(wid, "WR")]]
                    if (wid, "FLEX") in x:
                        objective_terms += [bonus * x[(wid, "FLEX")]]

    prob += lpSum(objective_terms)

    # Constraints: each slot filled by exactly its count
    for slot, count in slot_reqs:
        prob += lpSum([x[(pid, s)] for (pid, s) in x if s == slot]) == count

    # One slot max per player
    pids = set(pid for (pid, _s) in x)
    for pid in pids:
        prob += lpSum([var for (p, _s), var in x.items() if p == pid]) <= 1

    # Solve with CBC; fallback to heuristic if infeasible or error
    try:
        res = prob.solve(PULP_CBC_CMD(msg=False))
    except Exception:
        return greedy_fallback(session, week, objective, lam)
    if LpStatus.get(prob.status, "") != "Optimal":
        return greedy_fallback(session, week, objective, lam)

    # Build lineup and bench
    chosen: Dict[str, List[int]] = {slot: [] for slot, _ in slot_reqs}
    for (pid, slot), var in x.items():
        if var.value() and var.value() > 0.5:
            chosen[slot].append(pid)

    starters: List[Dict] = []
    bench: List[Dict] = []
    # select top bench by value (remaining rostered)
    selected_ids = {pid for ids in chosen.values() for pid in ids}
    # preload game info per team
    team_games = {}
    for g in session.exec(select(Game).where(Game.week == week)).all():
        team_games[g.team] = g
    for slot, _ in slot_reqs:
        for pid in chosen[slot]:
            p = session.get(Player, pid)
            g = team_games.get(p.team or "")
            starters.append({
                "player_id": pid,
                "name": p.name,
                "position": slot,
                "team": p.team,
                "injury": inj_map.get(pid),
                "home": (g.home if g else None),
                "weather": (g.weather if g else None),
                "value": round(values[pid], 2),
            })
    bench_pool = [pid for pid in pids if pid not in selected_ids]
    bench_sorted = sorted(bench_pool, key=lambda pid: values[pid], reverse=True)
    # de-dup by normalized name to avoid duplicates if DB still has remnants
    def _norm(n: str) -> str:
        n = n.lower().strip()
        for ch in ["’","‘","`","´","–","—"]:
            n = n.replace(ch, "'")
        return n
    seen_names: set[str] = set()
    for pid in bench_sorted:
        p = session.get(Player, pid)
        key = _norm(p.name)
        if key in seen_names:
            continue
        seen_names.add(key)
        g = team_games.get(p.team or "")
        bench.append({
            "player_id": pid,
            "name": p.name,
            "position": p.position,
            "team": p.team,
            "injury": inj_map.get(pid),
            "home": (g.home if g else None),
            "weather": (g.weather if g else None),
            "value": round(values[pid], 2),
        })

    # Simple rationale
    rationale = {pid: f"Projection {round(values[pid],2)}; injury/weather considered." for pid in selected_ids}
    return {"starters": starters, "bench": bench, "rationale": rationale}


def greedy_fallback(session: Session, week: int, objective: str, lam: float) -> Dict:
    # Very simple: pick top by slot greedily
    candidates = get_candidates(session, week)
    values: Dict[int, float] = {}
    for p, pr, pen in candidates:
        base = pr.expected if objective == "expected" else _risk_adjust(pr.expected, pr.stdev or 0.0, lam)
        values[p.id] = base + pen

    chosen: Dict[str, List[int]] = {slot: [] for slot, _ in LINEUP_SLOTS}
    used: set[int] = set()

    def pick_for_slot(slot: str, count: int, elig_pos: set[str]):
        nonlocal used
        pool = [(p, values[p.id]) for p, _pr, _pen in candidates if (p.position in elig_pos) and p.id not in used]
        for p, _v in sorted(pool, key=lambda t: t[1], reverse=True)[:count]:
            chosen[slot].append(p.id)
            used.add(p.id)

    for slot, count in LINEUP_SLOTS:
        if slot == "FLEX":
            pick_for_slot(slot, count, FLEX_POS)
        else:
            pick_for_slot(slot, count, {slot})

    starters: List[Dict] = []
    for slot, ids in chosen.items():
        for pid in ids:
            p = session.get(Player, pid)
            starters.append({"player_id": pid, "name": p.name, "position": slot, "value": round(values[pid], 2)})
    bench: List[Dict] = []
    bench_pool = [p.id for p, _pr, _pen in candidates if p.id not in used]
    seen_names: set[str] = set()
    for pid in sorted(bench_pool, key=lambda i: values[i], reverse=True):
        p = session.get(Player, pid)
        key = p.name.lower().strip()
        if key in seen_names:
            continue
        seen_names.add(key)
        g = team_games.get(p.team or "")
        bench.append({
            "player_id": pid,
            "name": p.name,
            "position": p.position,
            "team": p.team,
            "injury": inj_map.get(pid),
            "home": (g.home if g else None),
            "weather": (g.weather if g else None),
            "value": round(values[pid], 2),
        })
    rationale = {pid: f"Greedy selection value {round(values[pid],2)}." for pid in used}
    return {"starters": starters, "bench": bench, "rationale": rationale}
