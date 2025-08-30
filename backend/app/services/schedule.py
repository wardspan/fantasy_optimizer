from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
from sqlmodel import Session, select

from ..models import Game


def stadium_latlon(team: str) -> tuple[Optional[float], Optional[float]]:
    data_path = Path(__file__).resolve().parents[1] / "app" / "data" / "stadiums.json"
    if not data_path.exists():
        data_path = Path(__file__).resolve().parents[0] / ".." / "data" / "stadiums.json"
    try:
        data = json.loads(data_path.read_text())
        row = data.get(team)
        if row:
            return float(row.get("lat")), float(row.get("lon"))
    except Exception:
        pass
    return None, None


def upsert_game(
    session: Session,
    week: int,
    team: str,
    opponent: Optional[str],
    home: bool,
    kickoff_utc: Optional[datetime] = None,
) -> Game:
    game = session.exec(select(Game).where(Game.week == week, Game.team == team)).first()
    if not game:
        lat, lon = stadium_latlon(team)
        game = Game(week=week, team=team, opponent=opponent, home=home, kickoff_utc=kickoff_utc, lat=lat, lon=lon)
        session.add(game)
    else:
        game.opponent = opponent
        game.home = home
        if kickoff_utc:
            game.kickoff_utc = kickoff_utc
        if not game.lat or not game.lon:
            game.lat, game.lon = stadium_latlon(team)
    session.flush()
    return game


async def fetch_weather_for_week(session: Session, week: int) -> int:
    # For each game with lat/lon and kickoff, call Open-Meteo and store a simple summary
    cnt = 0
    games = session.exec(select(Game).where(Game.week == week)).all()
    async with httpx.AsyncClient(timeout=15) as client:
        for g in games:
            if not g.lat or not g.lon:
                continue
            # If kickoff missing, assume Sunday 18:00 UTC
            kickoff = g.kickoff_utc or datetime.utcnow().replace(hour=18, minute=0, second=0, microsecond=0)
            start_iso = (kickoff - timedelta(hours=2)).isoformat()
            end_iso = (kickoff + timedelta(hours=2)).isoformat()
            url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={g.lat}&longitude={g.lon}"
                f"&hourly=temperature_2m,precipitation_probability,wind_speed_10m"
                f"&start={start_iso}&end={end_iso}"
            )
            try:
                r = await client.get(url)
                if r.status_code // 100 != 2:
                    continue
                data = r.json()
                hourly = data.get("hourly", {})
                temps = hourly.get("temperature_2m", [])
                precs = hourly.get("precipitation_probability", [])
                winds = hourly.get("wind_speed_10m", [])
                # choose middle index
                if temps:
                    idx = min(len(temps) // 2, len(temps) - 1)
                    summary = {
                        "temp_c": temps[idx],
                        "precip_prob": precs[idx] if idx < len(precs) else None,
                        "wind_kmh": winds[idx] if idx < len(winds) else None,
                    }
                    g.weather = summary
                    g.updated_at = datetime.utcnow()
                    cnt += 1
            except Exception:
                continue
    session.commit()
    return cnt

