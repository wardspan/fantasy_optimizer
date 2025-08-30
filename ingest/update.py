from __future__ import annotations

import argparse
from sqlmodel import Session

from backend.app.db import engine
from ingest.providers import espn, fantasypros, injuries, adp, yahoo
from ingest.providers import dvp
from backend.app.services import sportsdata as sportsdata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", type=int, required=True)
    args = parser.parse_args()
    week = args.week
    with Session(engine) as session:
        # Pull projections from FantasyPros (public); ESPN projections are optional placeholder
        c2 = fantasypros.fetch_projections(session, week)
        c1 = espn.fetch_projections(session, week)
        c_sd = sportsdata.fetch_projections(session, week)
        c_yh = yahoo.fetch_projections(session, week)
        c3 = injuries.fetch_injuries(session, week)
        c4 = adp.fetch_adp(session)
        c5 = espn.fetch_adp(session)
        c6 = dvp.fetch_dvp(session)
        session.commit()
        print(f"Ingest complete. espn_proj {c1}, fantasypros_proj {c2}, sportsdata_proj {c_sd}, yahoo_proj {c_yh}, injuries {c3}, fp_adp {c4}, espn_adp {c5}, dvp {c6}")


if __name__ == "__main__":
    main()
