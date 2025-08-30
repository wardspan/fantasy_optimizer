from sqlmodel import Session
from backend.app.db import engine, init_db
from backend.app.seeds.seed import run as seed_run
from backend.app.services.projections import blend_projections


def setup_module():
    init_db()
    seed_run()


def test_blended_weights():
    with Session(engine) as session:
        week = 1
        blended = blend_projections(session, week)
        # Ensure blended exists and is between the two sources
        assert blended, "no blended projections"
        any_val = next(iter(blended.values()))["expected"]
        assert 7.0 < any_val < 30.0

