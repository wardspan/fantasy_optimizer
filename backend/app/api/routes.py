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
from ..services import sportsdata as sdata
from ..services.schedule import upsert_game, fetch_weather_for_week
from ..auth import create_token, auth_required, hash_password, verify_password
from ..models import User
from ..models import Roster, Player, RosterStatus, Injury, SettingsRow
from ingest.providers import fantasypros as fp_provider
from ingest.providers import espn as espn_provider
from ingest.providers import injuries as injuries_provider
from ingest.providers import adp as adp_provider
from ingest.providers import espn as espn_provider
from ingest.providers import dvp as dvp_provider


router = APIRouter(prefix="/api")


@router.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@router.post("/auth/login")
def auth_login(body: Dict[str, str], session: Session = Depends(get_session)) -> Dict[str, Any]:
    from ..settings import get_settings
    settings = get_settings()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if settings.app_password and not email:
        # Backward compatibility: allow shared password-only login when email absent
        if password != settings.app_password:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_token("user")
        return {"ok": True, "token": token}
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(email)
    return {"ok": True, "token": token}


@router.post("/auth/register")
def auth_register(body: Dict[str, str], session: Session = Depends(get_session)) -> Dict[str, Any]:
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    token = create_token(email)
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
    c_sd_proj = sdata.fetch_projections(session, week)
    try:
        from ingest.providers import yahoo as yahoo_provider
        c_yahoo_proj = yahoo_provider.fetch_projections(session, week)
    except Exception:
        c_yahoo_proj = 0
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
    return {"ok": True, "counts": {"fantasypros": c_fp, "espn": c_espn, "sportsdata_proj": c_sd_proj, "yahoo_proj": c_yahoo_proj, "injuries": c_inj, "adp_fp": c_adp_fp, "adp_espn": c_adp_espn}, "blended": len(blended)}


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


@router.get("/roster/my")
def my_roster(session: Session = Depends(get_session)) -> Dict[str, Any]:
    rows = session.exec(select(Roster, Player).join(Player, Roster.player_id == Player.id).where(Roster.my_team == True)).all()
    data = []
    for r, p in rows:
        data.append({
            "player_id": p.id,
            "name": p.name,
            "team": p.team,
            "position": p.position,
            "status": r.status.value,
        })
    return {"roster": data}


@router.get("/news/my-players")
def news_my_players(session: Session = Depends(get_session)) -> Dict[str, Any]:
    settings = session.get(SettingsRow, 1)
    current_week = int((settings.data or {}).get("current_week", 1)) if settings else 1
    roster_rows = session.exec(select(Roster.player_id).where(Roster.my_team == True)).all()
    pids = [(row[0] if isinstance(row, tuple) else row) for row in roster_rows]
    items: list[dict] = []
    if pids:
        # Always include injury notes stored locally
        inj = session.exec(select(Injury, Player).join(Player, Injury.player_id == Player.id).where(Injury.week == current_week, Injury.player_id.in_(pids))).all()
        for i, p in inj:
            if i.status or i.note:
                items.append({
                    "player_id": p.id,
                    "name": p.name,
                    "team": p.team,
                    "status": i.status,
                    "note": i.note,
                    "week": current_week,
                    "kind": "injury",
                })
        # If SportsData.io key configured, enrich with recent player news
        try:
            # Unique teams from my roster
            teams = [t for (t,) in session.exec(select(Player.team).join(Roster, Roster.player_id == Player.id).where(Roster.my_team == True)).all() if t]
            team_news = sdata.news_by_teams(teams)
            # Map pid -> player record
            pid_to_player = {p.id: p for p in session.exec(select(Player).where(Player.id.in_(pids))).all()}
            matched_any = False
            for pid, p in pid_to_player.items():
                pitems = sdata.extract_player_news(team_news, p.name)
                for it in pitems[:3]:  # cap per player to avoid flood
                    items.append({
                        "player_id": pid,
                        "name": p.name,
                        "team": p.team,
                        "status": it.get("Categories") or it.get("Source") or "News",
                        "note": (it.get("Title") or "") + (": " + it.get("Content") if it.get("Content") else ""),
                        "timestamp": it.get("Updated") or it.get("UpdatedUtc") or it.get("TimeAgo"),
                        "kind": "news",
                    })
                    matched_any = True
            # If no specific player mentions found, include top general team news items
            if not matched_any:
                for it in team_news[:5]:
                    items.append({
                        "player_id": None,
                        "name": it.get("PlayerName") or it.get("Title") or "News",
                        "team": it.get("Team") or None,
                        "status": it.get("Categories") or it.get("Source") or "News",
                        "note": (it.get("Title") or "") + (": " + it.get("Content") if it.get("Content") else ""),
                        "timestamp": it.get("Updated") or it.get("UpdatedUtc") or it.get("TimeAgo"),
                        "kind": "news",
                    })
        except Exception:
            # If not configured or failed, silently skip external news
            pass
    return {"items": items}


@router.get("/standings")
def standings(session: Session = Depends(get_session)) -> Dict[str, Any]:
    try:
        table = espn_provider.fetch_standings()
        if table:
            return {"table": table, "source": "espn"}
    except Exception:
        pass
    table = [{"team": "Standings unavailable", "record": "-", "points_for": 0}]
    return {"table": table, "source": "placeholder"}


@router.get("/dashboard/cards")
def dashboard_cards(session: Session = Depends(get_session)) -> Dict[str, Any]:
    # Compose a set of carousel cards for the dashboard
    settings = session.get(SettingsRow, 1)
    week = int((settings.data or {}).get("current_week", 1)) if settings else 1
    # Injury timelines
    inj = session.exec(select(Injury, Player).join(Player, Injury.player_id == Player.id).where(Injury.week == week)).all()
    injury_cards = []
    for i, p in inj:
        if i.status or i.note:
            tag = 'Expected to play' if (i.status or '').lower()== 'questionable' and (i.note or '').lower().find('expected')>=0 else (i.status or 'Update')
            injury_cards.append({"type":"injury","player":p.name,"team":p.team,"tag":tag,"status": i.status, "note":i.note,"timestamp":i.updated_at.isoformat()})
    # Bye week alerts
    bye_cards = []
    starters = session.exec(select(Roster, Player).join(Player, Roster.player_id==Player.id).where(Roster.my_team==True, Roster.status==RosterStatus.start)).all()
    for r, p in starters:
        if p.bye_week and p.bye_week == week+1:
            # find bench replacement same position
            bench = session.exec(select(Roster, Player).join(Player, Roster.player_id==Player.id).where(Roster.my_team==True, Roster.status==RosterStatus.bench, Player.position==p.position)).all()
            repl = bench[0][1].name if bench else None
            bye_cards.append({"type":"bye","player":p.name,"team":p.team,"position":p.position,"bye_week":p.bye_week,"replacement":repl})
    # Weather warnings (high wind / heavy rain) for starters
    from ..models import Game
    team_games = {g.team: g for g in session.exec(select(Game).where(Game.week==week)).all()}
    weather_cards = []
    for r,p in starters:
        g = team_games.get(p.team or "")
        wx = g.weather if g else None
        if wx:
            wind = (wx.get('wind_kmh') or 0)
            precip = (wx.get('precip_prob') or 0)
            if (p.position in ('QB','K') and wind and wind>=25) or (precip and precip>=60):
                weather_cards.append({"type":"weather","player":p.name,"team":p.team,"wx":wx})
    # Late swap reminders
    swap_cards = []
    import datetime as _dt
    for r,p in starters:
        g = team_games.get(p.team or "")
        if g and g.kickoff_utc and g.kickoff_utc.weekday()==6 and g.kickoff_utc.hour>=20:
            swap_cards.append({"type":"late_swap","player":p.name,"team":p.team,"kickoff":g.kickoff_utc.isoformat()})
    # Waiver watchlist (top 3)
    from ..services.waivers import waiver_suggestions
    ww = waiver_suggestions(session, week)
    waiver_cards = [{"type":"waiver","name":w['name'],"team":w['position'],"vorp_delta":w['vorp_delta'],"faab":w['faab_bid']} for w in ww[:3]]
    # Trade pulse (simple pulse using vorp totals)
    from ..services.vorp import compute_vorp
    vorp = compute_vorp(session, week)
    my_ids = [r.player_id for r in session.exec(select(Roster).where(Roster.my_team==True)).all()]
    total_vorp = sum(vorp.get(pid,0) for pid in my_ids)
    trade_cards = [{"type":"trade_pulse","summary":f"Roster VORP total {round(total_vorp,1)} — Explore 1-2 upgrades at weakest positions."}]
    # Matchup (S.o.S via DVP): flag easy (rank high fp allowed) or tough (rank low fp allowed)
    from ..models import DVP
    matchup_cards = []
    dvp_map: Dict[tuple, DVP] = {}
    for d in session.exec(select(DVP)).all():
        dvp_map[(d.team, d.position)] = d
    for r,p in starters:
        g = team_games.get(p.team or "")
        opp = g.opponent if g else None
        if opp:
            d = dvp_map.get((opp, p.position))
            if d and d.rank:
                # Assume higher rank = easier (more points allowed). Thresholds: top 10 easy, bottom 10 tough
                tag = None
                if d.rank <= 10:
                    tag = "🔥 Easy matchup"
                elif d.rank >= 23:
                    tag = "🧊 Tough matchup"
                if tag:
                    matchup_cards.append({"type":"matchup","player":p.name,"team":p.team,"position":p.position,"opponent":opp,"rank":d.rank,"fp_allowed":d.fp_allowed,"tag":tag})
    return {"injuries": injury_cards, "byes": bye_cards, "weather": weather_cards, "late_swap": swap_cards, "waivers": waiver_cards, "trade": trade_cards, "matchups": matchup_cards}


@router.post("/admin/update-everything")
def update_everything(week: int, body: Dict[str, Any] | None = None, session: Session = Depends(get_session)) -> Dict[str, Any]:
    body = body or {}
    # Ingest
    c_fp = fp_provider.fetch_projections(session, week)
    c_espn = espn_provider.fetch_projections(session, week)
    c_sd_proj = sdata.fetch_projections(session, week)
    try:
        from ingest.providers import yahoo as yahoo_provider
        c_yahoo_proj = yahoo_provider.fetch_projections(session, week)
    except Exception:
        c_yahoo_proj = 0
    injuries_provider.fetch_injuries(session, week)
    adp_fp = adp_provider.fetch_adp(session)
    adp_es = espn_provider.fetch_adp(session)
    try:
      dvp_count = dvp_provider.fetch_dvp(session)
    except Exception:
      dvp_count = 0
    # Optional SportsData.io injuries
    sd_inj = 0
    try:
        sd_inj = sdata.fetch_injuries(session, week)
    except Exception:
        sd_inj = 0
    session.commit()
    # Optional schedule import
    sched_csv = body.get("schedule_csv")
    imported = 0
    if sched_csv:
        lines = [ln.strip() for ln in sched_csv.strip().splitlines() if ln.strip()]
        header = [h.strip().lower() for h in lines[0].split(",")]
        from datetime import datetime
        for line in lines[1:]:
            cols=[c.strip() for c in line.split(",")]
            row=dict(zip(header, cols))
            team=row.get('team'); opp=row.get('opponent'); home=row.get('home','1') in ('1','true','TRUE','yes'); ko=row.get('kickoff_iso')
            dt=None
            if ko:
                try: dt=datetime.fromisoformat(ko)
                except: dt=None
            if team:
                upsert_game(session, week=week, team=team.upper(), opponent=(opp or None), home=home, kickoff_utc=dt)
                imported+=1
        session.commit()
    # Blend
    blended = blend_projections(session, week)
    for pid, data_b in blended.items():
        row = session.exec(select(Projection).where(Projection.player_id == pid, Projection.week == week, Projection.source == "blended")).first()
        if not row:
            session.add(Projection(player_id=pid, week=week, source="blended", expected=data_b["expected"], stdev=1.5))
        else:
            row.expected = data_b["expected"]
    session.commit()
    # Weather: run async fetch from thread context safely
    import anyio
    anyio.from_thread.run(fetch_weather_for_week, session, week)
    # Optimize
    result = optimize_lineup(session, week=week, objective="risk", lam=0.35, stack_bonus=True)
    return {"ok": True, "counts": {"fp_proj": c_fp, "espn_proj": c_espn, "sportsdata_proj": c_sd_proj, "yahoo_proj": c_yahoo_proj, "adp_fp": adp_fp, "adp_espn": adp_es, "dvp": dvp_count, "sportsdata_inj": sd_inj, "schedule_imported": imported, "blended": len(blended)}, "lineup": result}


@router.post("/admin/backfill-teams")
def backfill_teams(session: Session = Depends(get_session)) -> Dict[str, Any]:
    # Re-scrape ADP (FantasyPros) to attach teams to players missing team
    count_before = session.exec(text("select count(*) from player where team is null or team = ''")).first()[0]
    c_adp = adp_provider.fetch_adp(session)
    session.commit()
    count_after = session.exec(text("select count(*) from player where team is null or team = ''")).first()[0]
    return {"ok": True, "adp_rows": c_adp, "missing_teams_before": count_before, "missing_teams_after": count_after}
