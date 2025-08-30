from __future__ import annotations

from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import Session, select

from ..services.alerts import send_slack_message
from ..db import engine
from ..models import SettingsRow, Player
from ..services.projections import blend_projections
from ..services.optimizer import optimize_lineup
from ..services.schedule import upsert_game, fetch_weather_for_week
from ingest.providers import fantasypros as fp_provider
from ingest.providers import espn as espn_provider
from ingest.providers import injuries as injuries_provider
from ingest.providers import adp as adp_provider


def setup_scheduler() -> AsyncIOScheduler:
    sched = AsyncIOScheduler()

    async def weekly_friday():
        # Auto-ingest for upcoming week, blend projections, make sure weather is fetched
        with Session(engine) as session:
            settings = session.get(SettingsRow, 1)
            data = settings.data if settings else {}
            week = int(data.get("current_week", 1))
            # Ingest projections and injuries
            fp_provider.fetch_projections(session, week)
            espn_provider.fetch_projections(session, week)
            injuries_provider.fetch_injuries(session, week)
            # Both ADPs
            adp_provider.fetch_adp(session)
            espn_provider.fetch_adp(session)
            session.commit()
            # Blend and upsert 'blended'
            blended = blend_projections(session, week)
            from ..models import Projection
            for pid, data_b in blended.items():
                row = session.exec(select(Projection).where(Projection.player_id == pid, Projection.week == week, Projection.source == "blended")).first()
                if not row:
                    session.add(Projection(player_id=pid, week=week, source="blended", expected=data_b["expected"], stdev=1.5))
                else:
                    row.expected = data_b["expected"]
            # Ensure game rows for weather by team seen in players
            teams = {p.team for p in session.exec(select(Player)).all() if p.team}
            for team in teams:
                upsert_game(session, week=week, team=team, opponent=None, home=True, kickoff_utc=None)
            session.commit()
        # Update weather asynchronously after committing games
        with Session(engine) as session:
            await fetch_weather_for_week(session, week)
        await send_slack_message(f"Auto-ingest complete for week {week}. Weather updated. Review draft/waivers if applicable.")

    async def sunday_check():
        # Coach mode: refresh injuries/weather, re-optimize and notify
        with Session(engine) as session:
            settings = session.get(SettingsRow, 1)
            data = settings.data if settings else {}
            week = int(data.get("current_week", 1))
            injuries_provider.fetch_injuries(session, week)
            session.commit()
        with Session(engine) as session:
            await fetch_weather_for_week(session, week)
        with Session(engine) as session:
            result = optimize_lineup(session, week=week, objective="risk", lam=0.35, stack_bonus=True)
        starters = ", ".join(f"{s['position']} {s['name']}" for s in result.get('starters', []))
        await send_slack_message(f"Coach Mode Week {week}: Risk-adjusted lineup set: {starters}")

    # Default cron: Friday 10:00 and Sunday 11:00 (UTC by default)
    sched.add_job(weekly_friday, "cron", day_of_week="fri", hour=10, minute=0)
    sched.add_job(sunday_check, "cron", day_of_week="sun", hour=11, minute=0)
    sched.start()
    return sched
