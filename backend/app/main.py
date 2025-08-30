from __future__ import annotations

import json
from pathlib import Path

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .models import SettingsRow, Player
from sqlmodel import select
from .api.routes import router
from .jobs.scheduler import setup_scheduler
from sqlmodel import Session
from .db import engine


app = FastAPI(title="fantasy-optimizer")
app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _background_bootstrap() -> None:
    try:
        init_db()
        with Session(engine) as session:
            if not session.get(SettingsRow, 1):
                data_path = Path(__file__).parent / "data" / "scoring.json"
                data = json.loads(data_path.read_text())
                session.add(SettingsRow(id=1, data=data))
                session.commit()
            has_player = session.exec(select(Player)).first()
            if not has_player:
                from .seeds.seed import run as seed_run
                seed_run()
    except Exception:
        # swallow; endpoints can proceed once DB comes up
        pass


@app.on_event("startup")
async def on_startup() -> None:
    setup_scheduler()
    asyncio.get_running_loop().create_task(_background_bootstrap())
