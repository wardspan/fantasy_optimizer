from __future__ import annotations

from datetime import datetime
from sqlmodel import Session, select

from ..db import engine
from ..models import Player, Roster, RosterStatus, Projection, ADP


def run() -> None:
    demo_players = [
        ("Patrick Mahomes", "QB", "KC"),
        ("Josh Allen", "QB", "BUF"),
        ("Christian McCaffrey", "RB", "SF"),
        ("Bijan Robinson", "RB", "ATL"),
        ("Justin Jefferson", "WR", "MIN"),
        ("Ja'Marr Chase", "WR", "CIN"),
        ("Travis Kelce", "TE", "KC"),
        ("Amon-Ra St. Brown", "WR", "DET"),
        ("Saquon Barkley", "RB", "PHI"),
        ("Tyreek Hill", "WR", "MIA"),
        ("Harrison Butker", "K", "KC"),
        ("49ers D/ST", "DST", "SF"),
        ("Chiefs D/ST", "DST", "KC"),
        ("Greg Zuerlein", "K", "NYJ"),
    ]
    with Session(engine) as session:
        players = []
        for name, pos, team in demo_players:
            p = session.exec(select(Player).where(Player.name == name)).first()
            if not p:
                p = Player(name=name, position=pos, team=team)
                session.add(p)
                session.flush()
            players.append(p)
        # Add roster: mark top as my team, others as FA
        my_ids = {players[i].id for i in range(min(9, len(players)))}
        for p in players:
            r = session.exec(select(Roster).where(Roster.player_id == p.id)).first()
            if not r:
                r = Roster(player_id=p.id, status=RosterStatus.start if p.position in {"QB","RB","WR","TE","K","DST"} else RosterStatus.bench, my_team=(p.id in my_ids))
                if not r.my_team:
                    r.status = RosterStatus.fa
                session.add(r)
        # Add simple projections for week 1
        week = 1
        for p in players:
            for src, exp in [("espn", 10.0), ("fantasypros", 9.0)]:
                base = 0.0
                if p.position == "QB":
                    base = 22.0
                elif p.position == "RB":
                    base = 16.0
                elif p.position == "WR":
                    base = 15.0
                elif p.position == "TE":
                    base = 12.0
                elif p.position == "K":
                    base = 8.0
                elif p.position == "DST":
                    base = 7.0
                exp_val = base + (2.0 if src == "espn" else 0.0)
                pr = session.exec(select(Projection).where(Projection.player_id == p.id, Projection.week == week, Projection.source == src)).first()
                if not pr:
                    session.add(Projection(player_id=p.id, week=week, source=src, expected=exp_val, stdev=2.0))
        # ADP
        for i, p in enumerate(players, start=1):
            a = session.exec(select(ADP).where(ADP.player_id == p.id)).first()
            if not a:
                session.add(ADP(player_id=p.id, source="espn", rank=float(i)))
        session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    run()
