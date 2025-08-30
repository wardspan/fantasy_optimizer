from sqlmodel import Session, select
from backend.app.db import engine, init_db
from backend.app.seeds.seed import run as seed_run
from backend.app.services.waivers import waiver_suggestions
from backend.app.services.trades import evaluate_trade
from backend.app.models import Player


def setup_module():
    init_db()
    seed_run()


def test_waiver_faab_bounds():
    with Session(engine) as session:
        recs = waiver_suggestions(session, week=1)
        for r in recs:
            assert 1 <= r["faab_bid"] <= 20


def test_trade_symmetry():
    with Session(engine) as session:
        # Pick two ids for a symmetric check
        plist = session.exec(select(Player)).all()
        a, b = plist[0].id, plist[1].id
        res1 = evaluate_trade(session, 1, [a], [b])
        res2 = evaluate_trade(session, 1, [b], [a])
        assert abs(res1["delta_my"] + res2["delta_my"]) < 1e-6
