# Agents Guide

This document helps automation (and humans) work effectively in this repo. It summarizes the architecture, primary workflows, and the most common operations (ingest, optimize, deploy) with the minimal context needed to make correct changes.

## Architecture (High Level)

- Backend: FastAPI (Python 3.11) + SQLModel (SQLAlchemy) + Pydantic v2
  - Services: optimizer (PuLP + CBC), projections blender, waivers, trades, schedule/weather, alerts (Slack)
  - Jobs: APScheduler for weekly ingest/coach mode
  - DB: Postgres (Railway in prod) — models in `backend/app/models.py`
  - Settings via env and `settings.data` row (JSON) — see `SettingsRow`
- Ingest: `ingest/` pulls free-data sources (FantasyPros, ESPN ADP, injuries), provides a CLI
- Frontend: React + Vite + TypeScript + Tailwind (dark mode), responsive
  - Pages under `frontend/src/pages`
  - API helper `frontend/src/api.ts` forwards Authorization token and supports `VITE_API_BASE`
- Docker: `docker-compose.yml` for local dev, `docker/api.Dockerfile` and `docker/web.Dockerfile`

## Key Flows

- Ingest & Blend
  - CLI: `python -m ingest.update --week <N>` (inside API container)
  - API one-click: `POST /api/projections/ingest-blend?week=N` (Dashboard button)
  - Blender uses provider weights; stored in `settings.data.weights`
- Weather & Schedule
  - Model `Game` stores per-team per-week home/away, kickoff, lat/lon, weather
  - Import schedule (CSV): `POST /api/admin/schedule/import?week=N` with body `{ csv: "team,opponent,home,kickoff_iso\n..." }`
  - Weather update: `POST /api/admin/weather/update?week=N` (Open‑Meteo)
- Weekly Automation (APScheduler)
  - Friday: ingest FP/ESPN projections + injuries + both ADPs, blend, ensure games, fetch weather, Slack summary
  - Sunday (Coach Mode): refresh injuries + weather, re-optimize risk lineup, Slack summary
  - Uses `settings.data.current_week`; set via Settings UI
- Lineup Optimization
  - ILP (PuLP + CBC solver) with fallback greedy
  - Objectives: risk-adjusted (expected − λ·stdev) or expected
  - Badges: Team, Injury, Home/Away, Weather, Stack
- Draft Helper
  - Dual ADP (FantasyPros + ESPN), VORP, Reach (prefers ESPN ADP), color badges

## Endpoints (Selected)

- Settings: `GET/POST /api/settings`
- Health: `GET /api/healthz`
- Ingest: `POST /api/projections/ingest-blend?week=`
- Lineups: `GET /api/lineup/optimal?week=&objective=risk|expected`
- What-if: `POST /api/whatif/lineup`
- Waivers: `GET /api/waivers/suggestions?week=`
- Trades: `POST /api/trades/evaluate`
- Draft: `GET /api/draft/best-picks?round=&pick=`
- Alerts test: `POST /api/alerts/test`
- ESPN roster (optional cookies): `POST /api/espn/import-roster?week=`
- Admin (duplicates/tools):
  - `POST /api/admin/cleanup/merge-duplicates`
  - `GET /api/admin/duplicates`
  - `POST /api/admin/backfill-teams`
  - `POST /api/admin/schedule/import?week=`
  - `POST /api/admin/weather/update?week=`

## Env & Auth

- APP_PASSWORD: shared password for login (optional). If set, UI requires login.
- AUTH_SECRET: token signing key (required if APP_PASSWORD set)
- DATABASE_URL: Railway/Heroku‑style Postgres URL (preferred in prod). Fallback to POSTGRES_*.
- SLACK_WEBHOOK_URL: Slack alerts (optional)
- ESPN_S2 / SWID / LEAGUE_ID / TEAM_ID: optional for read-only ESPN roster import

## Development

- Start: `make up` (API: 8000, Web: 5173)
- Dev API reload: `make up-dev`
- Tests: `make test`
- Lint/format: `ruff` + `black` for backend, ESLint + Prettier for frontend
- Seed demo: auto on first API start; or `docker compose exec api python -m backend.app.seeds.seed`

## Deployment

- Backend (Railway): attach Postgres; set envs (DATABASE_URL, APP_PASSWORD, AUTH_SECRET, SLACK_WEBHOOK_URL). Service listens on `$PORT`.
- Frontend (Vercel): set `VITE_API_BASE` to the Railway API URL; build `frontend` (Vite) with `dist` output.

## Conventions & Tips

- Data hygiene:
  - Normalize names: strip team tokens/suffixes; dedupe via `merge-duplicates`
  - `backfill-teams` fills team if missing using ADP data
- Optimizer:
  - Keep ILP constraints minimal and readable; fallback should mirror constraints
  - Expose new badges by enriching starter/bench dicts in `optimizer.py`
- Schedule/Weather:
  - If exact kickoff isn’t known, use a typical Sunday UTC slot; weather still fetched around kickoff window
- Draft Helper:
  - Prefer ESPN ADP for Reach if available; otherwise FP ADP
  - Keep beginner‑friendly annotations

## Safe Change Patterns

- Add a new endpoint:
  - Schema in `schemas.py` (if needed); route in `api/routes.py`; service code under `services/`
- Extend models:
  - Update `models.py`, run `SQLModel.metadata.create_all` on startup (already happens)
- Frontend additions:
  - Keep components small; leverage `card`, `badge`, dark classes
  - Use `api.ts` and inherit Authorization header automatically

## Known Pitfalls

- If badges don’t show: ensure ingest was run, schedule imported, weather fetched (or wait for automation). Players need `team` and injuries for badges.
- Login: Type APP_PASSWORD on the login screen; AUTH_SECRET is not the password.
- Vercel calls must use `VITE_API_BASE` to reach the Railway API; set and redeploy.

