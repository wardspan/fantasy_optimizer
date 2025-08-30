from __future__ import annotations

from typing import Dict
from io import StringIO
import re
import httpx
import pandas as pd
from sqlmodel import Session, select

from backend.app.models import DVP


POS_SLUG = {"QB": "qb", "RB": "rb", "WR": "wr", "TE": "te", "K": "k"}


def _norm_team(t: str) -> str:
    t = (t or "").strip().upper()
    # Normalize some variations
    m = re.match(r"([A-Z]{2,3})", t)
    return m.group(1) if m else t


def fetch_dvp(session: Session) -> int:
    count = 0
    with httpx.Client(timeout=20) as client:
        for pos, slug in POS_SLUG.items():
            url = f"https://www.fantasypros.com/nfl/defense-vs-position/{slug}.php"
            try:
                r = client.get(url)
                r.raise_for_status()
            except Exception:
                # Try alternative path without .php
                try:
                    alt = f"https://www.fantasypros.com/nfl/defense-vs-position/{slug}"
                    r = client.get(alt)
                    r.raise_for_status()
                except Exception:
                    continue
            dfs = pd.read_html(StringIO(r.text))
            if not dfs:
                continue
            df = dfs[0]
            df.columns = [str(c).strip().upper() for c in df.columns]
            # Look for TEAM and FPTS columns
            team_col = next((c for c in df.columns if c in ("TEAM","DEFENSE")), df.columns[0])
            fpts_col = next((c for c in df.columns if "FPTS" in c or "FANTASY POINTS" in c), None)
            if not fpts_col:
                # sometimes "PTS" used
                fpts_col = next((c for c in df.columns if c == "PTS"), None)
            # Rank is usually the index +1 or a RANK column
            rank_col = next((c for c in df.columns if c == "RANK"), None)
            for idx, row in df.iterrows():
                team = _norm_team(str(row.get(team_col, "")))
                if not team:
                    continue
                fp = None
                try:
                    v = row.get(fpts_col) if fpts_col else None
                    if v is not None:
                        fp = float(v)
                except Exception:
                    fp = None
                if rank_col:
                    try:
                        rank = int(row.get(rank_col))
                    except Exception:
                        rank = None
                else:
                    rank = idx + 1
                dvp = session.exec(select(DVP).where(DVP.team == team, DVP.position == pos)).first()
                if not dvp:
                    dvp = DVP(team=team, position=pos)
                    session.add(dvp)
                dvp.rank = rank
                dvp.fp_allowed = fp
                count += 1
    session.commit()
    return count
