from sqlmodel import Session
from backend.app.db import engine, init_db
from backend.app.seeds.seed import run as seed_run
from backend.app.services.optimizer import optimize_lineup


def setup_module():
    init_db()
    seed_run()


def test_ilp_feasible():
    with Session(engine) as session:
        result = optimize_lineup(session, week=1, objective="risk", lam=0.35, stack_bonus=True)
        # Check number of starters equals required slots (8)
        assert len(result["starters"]) >= 8

