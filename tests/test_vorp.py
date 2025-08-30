from sqlmodel import Session
from backend.app.db import engine, init_db
from backend.app.seeds.seed import run as seed_run
from backend.app.services.vorp import compute_replacement_levels, compute_vorp


def setup_module():
    init_db()
    seed_run()


def test_replacement_levels_and_vorp():
    with Session(engine) as session:
        repl = compute_replacement_levels(session, week=1)
        assert set(repl.keys()) >= {"QB","RB","WR","TE","K","DST"}
        vorp = compute_vorp(session, week=1)
        assert vorp, "empty VORP"
        # Some player should have positive VORP
        assert any(v > 0 for v in vorp.values())

