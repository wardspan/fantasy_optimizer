from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy import text

from ..db import get_session
from sqlalchemy import text
from ..models import SettingsRow, Player, Roster, RosterStatus, Projection, LineupResult, WaiverRec, TradeEval
from ..schemas import (
    SettingsIn,
    RosterImportRequest,
    LineupResponse,
    WhatIfRequest,
    TradeRequest,
    TradeResponse,
)
from ..services.projections import blend_projections
from ..services.optimizer import optimize_lineup
from ..services.waivers import waiver_suggestions
from ..services.trades import evaluate_trade
from ..services.draft import best_picks_by_position
from ..services.alerts import send_slack_message
from ..services.schedule import upsert_game, fetch_weather_for_week
from ..auth import create_token, auth_required
from ingest.providers import fantasypros as fp_provider
from ingest.providers import espn as espn_provider
from ingest.providers import injuries as injuries_provider
from ingest.providers import adp as adp_provider
from ingest.providers import espn as espn_provider


router = APIRouter(prefix="/api")


@router.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@router.post("/auth/login")
def auth_login(body: Dict[str, str]) -> Dict[str, Any]:
    from ..settings import get_settings
    settings = get_settings()
    if not settings.app_password:
        # auth not configured
        token = create_token("anonymous")
        return {"ok": True, "token": token}
    if body.get("password") != settings.app_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token("user")
    return {"ok": True, "token": token}


@router.post("/settings")
def save_settings(payload: SettingsIn, session: Session = Depends(get_session)) -> Dict[str, Any]:
    row = session.get(SettingsRow, 1)
    if not row:
        row = SettingsRow(id=1, data=payload.data)
        session.add(row)
    else:
        row.data = payload.data
    session.commit()
    return {"ok": True}


@router.get("/settings")
def get_settings_api(session: Session = Depends(get_session)) -> Dict[str, Any]:
    row = session.get(SettingsRow, 1)
    return {"data": (row.data if row else {})}


@router.post("/roster/import")
def import_roster(req: RosterImportRequest, session: Session = Depends(get_session)) -> Dict[str, Any]:
    # Expect CSV header: name,position,team,status
    added = 0
    lines = [ln.strip() for ln in req.csv.strip().splitlines() if ln.strip()]
    if not lines:
        raise HTTPException(400, "Empty CSV")
    header = [h.strip().lower() for h in lines[0].split(",")]
    for line in lines[1:]:
        cols = [c.strip() for c in line.split(",")]
        row = dict(zip(header, cols))
        name = row.get("name")
        pos = row.get("position", "FLEX").upper()
        team = row.get("team")
        status = row.get("status", "bench").lower()
        if not name:
            continue
        player = session.exec(select(Player).where(Player.name == name)).first()
        if not player:
            player = Player(name=name, position=pos, team=team)
            session.add(player)
            session.flush()
        roster = session.exec(select(Roster).where(Roster.player_id == player.id)).first()
        if not roster:
            roster = Roster(player_id=player.id, status=RosterStatus(status), my_team=True)
            session.add(roster)
        else:
            roster.status = RosterStatus(status)
        added += 1
    session.commit()
    return {"ok": True, "count": added}


@router.post("/projections/update")
def update_projections(week: int, session: Session = Depends(get_session)) -> Dict[str, Any]:
    # Assume ingest has inserted source-specific projections; compute blended and store/override source 'blended'
    blended = blend_projections(session, week)
    for pid, data in blended.items():
        # Upsert as source 'blended'
        row = session.exec(select(Projection).where(Projection.player_id == pid, Projection.week == week, Projection.source == "blended")).first()
        if not row:
            row = Projection(player_id=pid, week=week, source="blended", expected=data["expected"], stdev=1.5)
            session.add(row)
        else:
            row.expected = data["expected"]
    session.commit()
    return {"ok": True, "blended_count": len(blended)}


@router.post("/projections/ingest-blend")
def ingest_and_blend(week: int, session: Session = Depends(get_session)) -> Dict[str, Any]:
    # Ensure DB connection is live
    session.exec(text("SELECT 1"))
    c_fp = fp_provider.fetch_projections(session, week)
    c_espn = espn_provider.fetch_projections(session, week)
    c_inj = injuries_provider.fetch_injuries(session, week)
    c_adp_fp = adp_provider.fetch_adp(session)
    c_adp_espn = espn_provider.fetch_adp(session)
    session.commit()
    blended = blend_projections(session, week)
    for pid, data in blended.items():
        row = session.exec(select(Projection).where(Projection.player_id == pid, Projection.week == week, Projection.source == "blended")).first()
        if not row:
            session.add(Projection(player_id=pid, week=week, source="blended", expected=data["expected"], stdev=1.5))
        else:
            row.expected = data["expected"]
    session.commit()
    return {"ok": True, "counts": {"fantasypros": c_fp, "espn": c_espn, "injuries": c_inj, "adp_fp": c_adp_fp, "adp_espn": c_adp_espn}, "blended": len(blended)}


@router.get("/lineup/optimal", response_model=LineupResponse)
def lineup_optimal(week: int, objective: str = "risk", stack: bool = False, session: Session = Depends(get_session)) -> LineupResponse:
    result = optimize_lineup(session, week=week, objective=objective, lam=0.35, stack_bonus=stack)
    # Save result
    session.add(LineupResult(week=week, objective=objective, results_json=result))
    session.commit()
    return LineupResponse(**result)


@router.post("/whatif/lineup", response_model=LineupResponse)
def whatif_lineup(req: WhatIfRequest, session: Session = Depends(get_session)) -> LineupResponse:
    # Apply overrides temporarily
    overrides = req.overrides or {}
    touched = []
    for pid, o in overrides.items():
        row = session.exec(select(Projection).where(Projection.player_id == pid, Projection.week == req.week)).first()
        if row:
            touched.append((row, row.expected, row.stdev))
            row.expected = o.get("expected", row.expected)
            row.stdev = o.get("stdev", row.stdev)
    session.commit()
    result = optimize_lineup(session, week=req.week, objective=req.objective, lam=req.lambda_risk, stack_bonus=False)
    # Revert overrides
    for row, exp, sd in touched:
        row.expected = exp
        row.stdev = sd
    session.commit()
    return LineupResponse(**result)


@router.get("/waivers/suggestions")
def waivers(week: int, session: Session = Depends(get_session)) -> Dict[str, Any]:
    recs = waiver_suggestions(session, week)
    session.add(WaiverRec(week=week, data={"recs": recs}))
    session.commit()
    return {"recs": recs}


@router.post("/trades/evaluate", response_model=TradeResponse)
def trade_eval(req: TradeRequest, week: int = 1, session: Session = Depends(get_session)) -> TradeResponse:
    data = evaluate_trade(session, week, req.players_in, req.players_out)
    session.add(TradeEval(data=data))
    session.commit()
    return TradeResponse(**data)


@router.get("/draft/best-picks")
def draft_best(round: int, pick: int, session: Session = Depends(get_session)) -> Dict[str, Any]:
    return best_picks_by_position(session, round, pick)


@router.post("/alerts/test")
async def alerts_test() -> Dict[str, Any]:
    ok = await send_slack_message("Test message from fantasy-optimizer")
    return {"ok": ok}


@router.post("/espn/import-roster")
def espn_import_roster(week: int = 1, session: Session = Depends(get_session)) -> Dict[str, Any]:
    res = espn_provider.fetch_private_roster(session, week=week)
    session.commit()
    return res


def _norm_name(s: str) -> str:
    s = (s or "").strip().lower()
    for ch in ["’", "‘", "`", "´", "–", "—"]:
        s = s.replace(ch, "'")
    # strip trailing team abbreviations or dst
    import re as _re
    s = _re.sub(r"\s+(?:[a-z]{2,3}|d\/st|dst)$", "", s)
    s = _re.sub(r"\b(jr|sr|ii|iii|iv|v)\.?$", "", s)
    while "  " in s:
        s = s.replace("  ", " ")
    return s


@router.post("/admin/cleanup/merge-duplicates")
def merge_duplicates(session: Session = Depends(get_session)) -> Dict[str, Any]:
    players = session.exec(select(Player)).all()
    groups: Dict[str, list[Player]] = {}
    for p in players:
        groups.setdefault(_norm_name(p.name), []).append(p)
    details = []
    merged = 0
    for key, plist in groups.items():
        if len(plist) <= 1:
            continue
        # choose canonical: prefer with espn_id, then with most projections, else lowest id
        # precompute projection counts
        proj_counts: Dict[int, int] = {}
        for (cnt_pid, cnt) in session.exec(text("select player_id, count(*) from projection group by player_id")).all():
            proj_counts[int(cnt_pid)] = int(cnt)
        def score(p: Player) -> tuple:
            return (1 if p.espn_id else 0, proj_counts.get(p.id or -1, 0), -(p.id or 0))
        canonical = sorted(plist, key=score, reverse=True)[0]
        dup_ids = [p.id for p in plist if p.id != canonical.id]
        if not dup_ids:
            continue
        # If canonical lacks team/position, fill from a duplicate
        if not canonical.team:
            for p in plist:
                if p.team:
                    canonical.team = p.team
                    break
        if (not canonical.position) or canonical.position == "FLEX":
            for p in plist:
                if p.position and p.position != "FLEX":
                    canonical.position = p.position
                    break
        # Re-point foreign keys in bulk
        for table in ("roster", "projection", "injury", "adp"):
            for dup_id in dup_ids:
                session.exec(text(f"update {table} set player_id = :canon where player_id = :dup").bindparams(canon=canonical.id, dup=dup_id))
        # Deduplicate ADP by keeping most recent per source for canonical
        session.exec(text(
            "delete from adp a using adp b "
            "where a.player_id = :pid and b.player_id = :pid and a.source = b.source and a.updated_at < b.updated_at"
        ).bindparams(pid=canonical.id))
        # Deduplicate Projections by keeping most recent per (week,source)
        session.exec(text(
            "delete from projection a using projection b "
            "where a.player_id = :pid and b.player_id = :pid and a.week = b.week and a.source = b.source and a.updated_at < b.updated_at"
        ).bindparams(pid=canonical.id))
        # Delete duplicate player rows
        for dup_id in dup_ids:
            session.exec(text("delete from player where id = :dup").bindparams(dup=dup_id))
        session.commit()
        details.append({"name": canonical.name, "canonical_id": canonical.id, "removed_ids": dup_ids})
        merged += 1
    return {"merged_groups": merged, "details": details}


@router.get("/admin/duplicates")
def list_duplicates(session: Session = Depends(get_session)) -> Dict[str, Any]:
    players = session.exec(select(Player)).all()
    groups: Dict[str, list[dict]] = {}
    for p in players:
        key = _norm_name(p.name)
        entry = {"id": p.id, "name": p.name, "team": p.team, "position": p.position}
        groups.setdefault(key, []).append(entry)
    dups = {k:v for k,v in groups.items() if len(v) > 1}
    return {"duplicate_groups": dups}


@router.post("/admin/schedule/import")
def import_schedule(csv: str, week: int, session: Session = Depends(get_session)) -> Dict[str, Any]:
    # CSV header: team,opponent,home(1/0),kickoff_iso(optional)
    lines = [ln.strip() for ln in csv.strip().splitlines() if ln.strip()]
    if not lines:
        raise HTTPException(400, "Empty CSV")
    header = [h.strip().lower() for h in lines[0].split(",")]
    added = 0
    for line in lines[1:]:
        cols = [c.strip() for c in line.split(",")]
        row = dict(zip(header, cols))
        team = row.get("team")
        opponent = row.get("opponent")
        home = row.get("home", "1") in ("1","true","TRUE","yes")
        kickoff_iso = row.get("kickoff_iso") or None
        from datetime import datetime
        kickoff = None
        if kickoff_iso:
            try:
                kickoff = datetime.fromisoformat(kickoff_iso)
            except Exception:
                kickoff = None
        if not team:
            continue
        upsert_game(session, week=week, team=team.upper(), opponent=(opponent or None), home=home, kickoff_utc=kickoff)
        added += 1
    session.commit()
    return {"ok": True, "imported": added}


@router.post("/admin/weather/update")
async def update_weather(week: int, session: Session = Depends(get_session)) -> Dict[str, Any]:
    cnt = await fetch_weather_for_week(session, week)
    return {"ok": True, "updated_games": cnt}


@router.post("/admin/backfill-teams")
def backfill_teams(session: Session = Depends(get_session)) -> Dict[str, Any]:
    # Re-scrape ADP (FantasyPros) to attach teams to players missing team
    count_before = session.exec(text("select count(*) from player where team is null or team = ''")).first()[0]
    c_adp = adp_provider.fetch_adp(session)
    session.commit()
    count_after = session.exec(text("select count(*) from player where team is null or team = ''")).first()[0]
    return {"ok": True, "adp_rows": c_adp, "missing_teams_before": count_before, "missing_teams_after": count_after}
