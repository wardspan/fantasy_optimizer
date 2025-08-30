from __future__ import annotations

import re
from typing import Dict, List, Optional

import httpx
from io import StringIO
import pandas as pd
from sqlmodel import Session

from ..util import upsert_projection, upsert_adp, get_or_create_player


POS_SLUG = {"QB": "qb", "RB": "rb", "WR": "wr", "TE": "te", "K": "k", "DST": "dst"}


def _extract_team(name_text: str, row_team: Optional[str]) -> Optional[str]:
    # Prefer explicit team column
    t = (row_team or "").strip().upper() if row_team else None
    if t and len(t) <= 3 and t.isalpha():
        return t
    # Try parentheses in name e.g., "Player (KC)"
    m = re.search(r"\(([^)]+)\)$", name_text)
    if m:
        tt = m.group(1).strip().upper()
        if 2 <= len(tt) <= 3 and tt.isalpha():
            return tt
    # Try trailing team token e.g., "Player KC"
    m2 = re.search(r"\s([A-Z]{2,3}|D\/ST|DST)$", name_text.strip())
    if m2:
        tt = m2.group(1).upper()
        if tt in ("DST","D/ST"):
            return "DST"
        return tt
    return None


def _clean_player_name(text: str) -> str:
    # Remove parentheses content and trailing team tokens
    s = re.sub(r"\s*\(.*\)$", "", text).strip()
    s = re.sub(r"\s+(?:[A-Z]{2,3}|D\/ST|DST)$", "", s)
    # Remove common suffixes like Jr., Sr., II, III
    s = re.sub(r"\b(JR|SR|II|III|IV|V)\.?$", "", s, flags=re.IGNORECASE).strip()
    return s


def _norm_col(col) -> str:
    # Flatten MultiIndex/tuple columns and normalize spacing/case
    if isinstance(col, tuple):
        parts = [str(p) for p in col if p and str(p).lower() != 'nan']
        s = " ".join(parts)
    else:
        s = str(col)
    return s.strip().upper()


def fetch_projections(session: Session, week: int, scoring: str = "PPR") -> int:
    count = 0
    with httpx.Client(timeout=20) as client:
        for pos, slug in POS_SLUG.items():
            url = f"https://www.fantasypros.com/nfl/projections/{slug}.php?week={week}&scoring={scoring}"
            r = client.get(url)
            r.raise_for_status()
            # Parse tables using pandas; FantasyPros exposes a projections table with FPTS
            dfs = pd.read_html(StringIO(r.text))
            if not dfs:
                continue
            df = dfs[0]
            # Normalize column names (handle MultiIndex/tuples)
            df.columns = [_norm_col(c) for c in df.columns]
            # Identify name and fantasy points columns
            name_candidates: List[str] = ["PLAYER", "PLAYER NAME", "NAME"]
            name_col = next((c for c in df.columns if c in name_candidates), df.columns[0])
            team_col = next((c for c in df.columns if c == "TEAM" or "TEAM" in c), None)
            fpts_col = None
            for c in df.columns:
                if "FPTS" in c or "FANTASY POINTS" in c:
                    fpts_col = c
                    break
            if not fpts_col:
                continue
            for _, row in df.iterrows():
                name_raw = str(row.get(name_col, "")).strip()
                team_guess = _extract_team(name_raw, str(row.get(team_col, "")) if team_col else None)
                name = _clean_player_name(name_raw)
                val_raw = row.get(fpts_col, 0)
                try:
                    fpts = float(val_raw)
                except Exception:
                    fpts = 0.0
                if not name or fpts <= 0:
                    continue
                p = get_or_create_player(session, name=name, position=pos, team=team_guess)
                upsert_projection(session, p, week, "fantasypros", fpts, stdev=2.5)
                count += 1
    return count


def fetch_adp_fantasypros(session: Session) -> int:
    url = "https://www.fantasypros.com/nfl/adp/overall.php"
    with httpx.Client(timeout=20) as client:
        r = client.get(url)
        r.raise_for_status()
        dfs = pd.read_html(StringIO(r.text))
        if not dfs:
            return 0
        df = dfs[0]
        # Normalize columns
        df.columns = [_norm_col(c) for c in df.columns]
        name_col = next((c for c in df.columns if c in ("PLAYER","PLAYER NAME","NAME")), df.columns[0])
        # Find ADP column by contains
        adp_col = next((c for c in df.columns if "ADP" in c or "AVG. DRAFT POSITION" in c), None)
        team_col = next((c for c in df.columns if c == "TEAM" or "TEAM" in c), None)
        if not adp_col:
            return 0
        count = 0
        for _, row in df.iterrows():
            try:
                raw = str(row[name_col])
                team_guess = _extract_team(raw, str(row.get(team_col, "")) if team_col else None)
                name = _clean_player_name(raw)
                team = team_guess
                adp = float(row[adp_col])
            except Exception:
                continue
            if not name:
                continue
            p = get_or_create_player(session, name=name, team=team)
            upsert_adp(session, p, "fantasypros", adp)
            count += 1
        return count
