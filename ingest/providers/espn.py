from __future__ import annotations

from typing import List, Tuple, Optional
import re
from io import StringIO
import httpx
import pandas as pd
from sqlmodel import Session, select
from backend.app.models import Player, Roster, RosterStatus
from backend.app.settings import get_settings
from ..util import upsert_projection, upsert_injury, upsert_adp, get_or_create_player


def fetch_projections(session: Session, week: int) -> int:
    # Demo: generate simple projections slightly higher for ESPN
    count = 0
    players = session.exec(select(Player)).all()
    for p in players:
        base = 20.0 if p.position == "QB" else 12.0
        upsert_projection(session, p, week, "espn", base + 2.0, stdev=2.0)
        count += 1
    return count


def fetch_injuries(session: Session, week: int) -> int:
    # Demo: mark everyone Active
    count = 0
    for p in session.exec(select(Player)).all():
        upsert_injury(session, p, week, "Active", note=None)
        count += 1
    return count


def fetch_adp(session: Session) -> int:
    # Scrape ESPN Live Draft Results (public) for ADP; best-effort
    # Example: https://fantasy.espn.com/football/livedraftresults?seasonId=2025
    import datetime as _dt
    season = _dt.datetime.utcnow().year
    url = f"https://fantasy.espn.com/football/livedraftresults?seasonId={season}"
    try:
        with httpx.Client(timeout=20) as client:
            r = client.get(url)
            r.raise_for_status()
            # Parse all tables and find the one with ADP-like column
            dfs = pd.read_html(StringIO(r.text))
            if not dfs:
                return 0
            count = 0
            # Helpers
            def _norm_col(col) -> str:
                if isinstance(col, tuple):
                    parts = [str(p) for p in col if p and str(p).lower() != 'nan']
                    s = " ".join(parts)
                else:
                    s = str(col)
                return s.strip().upper()

            def _clean_name(s: str) -> str:
                # Remove parentheses/team and trailing team, and common suffixes
                s2 = re.sub(r"\s*\(.*\)$", "", s).strip()
                s2 = re.sub(r"\s+(?:[A-Z]{2,3}|D\/ST|DST)$", "", s2)
                s2 = re.sub(r"\b(JR|SR|II|III|IV|V)\.?$", "", s2, flags=re.IGNORECASE).strip()
                return s2

            def _extract_team(name_text: str) -> Optional[str]:
                m = re.search(r"\(([^)]+)\)$", name_text)
                if m:
                    tt = m.group(1).strip().upper()
                    if 2 <= len(tt) <= 3 and tt.isalpha():
                        return tt
                m2 = re.search(r"\s([A-Z]{2,3}|D\/ST|DST)$", name_text.strip())
                if m2:
                    tt = m2.group(1).upper()
                    return "DST" if tt in ("DST","D/ST") else tt
                return None

            for df in dfs:
                df.columns = [_norm_col(c) for c in df.columns]
                name_col = next((c for c in df.columns if c in ("PLAYER","PLAYER NAME","NAME")), None)
                adp_col = next((c for c in df.columns if c in ("ADP","AVG PICK","AVERAGE PICK") or "ADP" in c or "AVERAGE" in c), None)
                if not name_col or not adp_col:
                    continue
                for _, row in df.iterrows():
                    raw = str(row.get(name_col, "")).strip()
                    if not raw:
                        continue
                    name = _clean_name(raw)
                    team = _extract_team(raw)
                    try:
                        adp = float(row.get(adp_col))
                    except Exception:
                        continue
                    if not name:
                        continue
                    p = get_or_create_player(session, name=name, team=team)
                    upsert_adp(session, p, "espn", adp)
                    count += 1
            return count
    except Exception:
        return 0


# --- Private league roster import (read-only) ---

POSITION_MAP = {
    1: "QB",
    2: "RB",
    3: "WR",
    4: "TE",
    5: "K",
    16: "DST",
}

LINEUP_SLOT_STARTERS = {0, 2, 4, 6, 23, 17, 16}  # QB,RB,WR,TE,FLEX,K,DST
LINEUP_SLOT_IR = {21}

TEAM_ID_TO_ABBR = {
    1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE", 6: "DAL", 7: "DEN", 8: "DET",
    9: "GB", 10: "TEN", 11: "IND", 12: "KC", 13: "LV", 14: "LAR", 15: "MIA", 16: "MIN",
    17: "NE", 18: "NO", 19: "NYG", 20: "NYJ", 21: "PHI", 22: "ARI", 23: "PIT", 24: "LAC",
    25: "SF", 26: "SEA", 27: "TB", 28: "WSH", 29: "CAR", 30: "JAX", 33: "BAL", 34: "HOU",
}


def fetch_private_roster(session: Session, week: int, season: int | None = None) -> dict:
    settings = get_settings()
    if not (settings.espn_s2 and settings.swid and settings.league_id and settings.team_id):
        return {"ok": False, "error": "Missing ESPN_S2/SWID/LEAGUE_ID/TEAM_ID env vars"}
    if season is None:
        # crude guess: use current year
        import datetime as _dt
        season = _dt.datetime.utcnow().year
    url = f"https://fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{settings.league_id}?scoringPeriodId={week}&view=mTeam&view=mRoster"
    cookies = {"espn_s2": settings.espn_s2, "SWID": settings.swid}
    with httpx.Client(timeout=20, cookies=cookies) as client:
        r = client.get(url)
        r.raise_for_status()
        data = r.json()
    team_id = int(settings.team_id)
    teams = data.get("teams", [])
    my_team = next((t for t in teams if t.get("id") == team_id), None)
    if not my_team:
        return {"ok": False, "error": f"Team {team_id} not found"}
    roster = my_team.get("roster", {}).get("entries", [])
    imported = 0
    starts = 0
    benches = 0
    irs = 0
    for e in roster:
        pinfo = e.get("playerPoolEntry", {}).get("player", {})
        name = pinfo.get("fullName")
        pos = POSITION_MAP.get(pinfo.get("defaultPositionId"), None)
        team_abbr = TEAM_ID_TO_ABBR.get(pinfo.get("proTeamId"))
        p = get_or_create_player(session, name=name, position=pos, team=team_abbr)
        # Determine status by lineupSlotId
        slot = e.get("lineupSlotId")
        status = RosterStatus.bench
        if slot in LINEUP_SLOT_STARTERS:
            status = RosterStatus.start
            starts += 1
        elif slot in LINEUP_SLOT_IR:
            status = RosterStatus.ir
            irs += 1
        else:
            benches += 1
        rrow = session.exec(select(Roster).where(Roster.player_id == p.id)).first()
        if not rrow:
            rrow = Roster(player_id=p.id, status=status, my_team=True)
            session.add(rrow)
        else:
            rrow.status = status
            rrow.my_team = True
        imported += 1
    return {"ok": True, "count": imported, "starts": starts, "bench": benches, "ir": irs}
