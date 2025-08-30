from __future__ import annotations

from typing import Any, Dict, Iterable, List

import httpx

from ..settings import get_settings
from sqlmodel import Session, select
from ingest.util import get_or_create_player, upsert_injury
from ..models import Player
from ingest.util import upsert_projection


BASE = "https://api.sportsdata.io/v3/nfl"


def _client() -> httpx.Client:
    settings = get_settings()
    if not settings.sportsdata_api_key:
        raise RuntimeError("SPORTSDATA_API_KEY not configured")
    headers = {"Ocp-Apim-Subscription-Key": settings.sportsdata_api_key}
    return httpx.Client(base_url=BASE, headers=headers, timeout=20)


def news_by_team(team: str) -> list[dict]:
    """Fetch recent news for a single NFL team abbreviation.

    Uses SportsData.io scores news endpoint. Returns empty on failure.
    """
    try:
        with _client() as client:
            # Endpoint: scores news by team
            # Reference: https://sportsdata.io/developers/api-documentation/nfl#scores
            r = client.get(f"/scores/json/NewsByTeam/{team}")
            if r.status_code // 100 != 2:
                return []
            data = r.json()
            return data if isinstance(data, list) else []
    except Exception:
        return []


def news_by_teams(teams: Iterable[str]) -> list[dict]:
    """Fetch and combine news items for multiple teams (dedup by NewsID)."""
    seen: set[int] = set()
    out: list[dict] = []
    for t in set([x for x in teams if x]):
        for item in news_by_team(t):
            nid = int(item.get("NewsID") or item.get("NewsId") or 0)
            if nid and nid in seen:
                continue
            seen.add(nid)
            out.append(item)
    return out


def extract_player_news(items: list[dict], player_name: str) -> list[dict]:
    """Return items that mention the player (by PlayerName or text match)."""
    name = (player_name or "").strip()
    name_lower = name.lower()
    out = []
    for it in items:
        pname = (it.get("PlayerName") or it.get("Player") or "").strip()
        title = (it.get("Title") or "").strip()
        content = (it.get("Content") or it.get("Body") or "").strip()
        if (pname and pname.lower() == name_lower) or (name and (name_lower in title.lower() or name_lower in content.lower())):
            out.append(it)
    return out


# --- Injury import ---

def _current_season() -> int:
    import datetime as _dt
    return _dt.datetime.utcnow().year


def fetch_injuries(session: Session, week: int) -> int:
    """Fetch NFL injuries for current season and upsert for given week.

    Maps basic status and note from SportsData.io items. Best-effort; silently returns 0 on failure.
    """
    try:
        season = _current_season()
        with _client() as client:
            r = client.get(f"/scores/json/Injuries/{season}")
            if r.status_code // 100 != 2:
                return 0
            data = r.json()
            if not isinstance(data, list):
                return 0
            count = 0
            for it in data:
                name = (it.get("Name") or it.get("PlayerName") or "").strip()
                if not name:
                    continue
                team = (it.get("Team") or it.get("TeamAbbr") or None)
                status = (it.get("InjuryStatus") or it.get("Status") or it.get("Practice") or "").strip() or "Update"
                note_parts = [p for p in [it.get("BodyPart"), it.get("PracticeStatus"), it.get("Notes") or it.get("Content")] if p]
                note = "; ".join(note_parts) if note_parts else None
                p = get_or_create_player(session, name=name, team=team)
                upsert_injury(session, p, week, status, note=note)
                count += 1
            session.commit()
            return count
    except Exception:
        return 0


def fetch_projections(session: Session, week: int) -> int:
    """Fetch fantasy projections and upsert as source 'sportsdata'.

    Attempts common SportsData.io projection shapes and gracefully returns 0 if unavailable.
    """
    try:
        season = _current_season()
        with _client() as client:
            # Try PlayerGameProjectionStatsByWeek (NFL Projections API)
            # https://sportsdata.io/developers/api-documentation/nfl#projections
            paths = [
                f"/projections/json/PlayerGameProjectionStatsByWeek/{season}/{week}",
                f"/fantasy/json/FantasyPlayers/{season}/{week}",  # fallback; may not exist
            ]
            data = None
            for path in paths:
                r = client.get(path)
                if r.status_code // 100 == 2:
                    try:
                        j = r.json()
                        if isinstance(j, list) and j:
                            data = j
                            break
                    except Exception:
                        pass
            if not data:
                return 0
            pos_map = {"Defense": "DST", "DEF": "DST"}
            count = 0
            for it in data:
                name = (it.get("Name") or it.get("PlayerName") or "").strip()
                if not name:
                    continue
                pos = (it.get("Position") or it.get("FantasyPosition") or "").strip().upper()
                pos = pos_map.get(pos, pos)
                team = (it.get("Team") or it.get("TeamAbbr") or it.get("PlayerTeam") or None)
                # Prefer PPR fantasy points if present
                fpts = None
                for key in ("FantasyPointsPPR", "FantasyPointsDraftKings", "FantasyPointsFanDuel", "FantasyPoints"):
                    v = it.get(key)
                    try:
                        fpts = float(v)
                        break
                    except Exception:
                        continue
                if fpts is None:
                    # As a last resort, skip
                    continue
                p = get_or_create_player(session, name=name, position=pos or None, team=team)
                upsert_projection(session, p, week, "sportsdata", fpts, stdev=2.2)
                count += 1
            session.commit()
            return count
    except Exception:
        return 0
