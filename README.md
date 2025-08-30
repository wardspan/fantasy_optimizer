# fantasy-optimizer

Production-ready, Dockerized Fantasy Football optimizer for ESPN leagues. Clean, responsive UI (light/dark, iPhone/iPad/Desktop). Features:
- Draft helper with VORP and dual ADP (FantasyPros + ESPN), reach guidance, clear badges.
- Weekly lineups: Risk-Adjusted vs Projected side-by-side with badges (Injury, Team, Home/Away, Weather, Stack).
- Waivers + FAAB, Trade evaluator, Slack alerts, simple login gate.

## Quick Start

1. Copy `.env.example` to `.env` and adjust if needed.
   - Optional auth: set `APP_PASSWORD` and `AUTH_SECRET` to require login.
2. Build and run services:

```
make up
```

3. Seed demo data (runs automatically on first API start). To re-run:

```
docker compose exec api python -m backend.app.seeds.seed
```

4. Open the web UI at http://localhost:5173 (login with APP_PASSWORD if set)

5. Health check: http://localhost:8000/api/healthz

### Tooling Versions

- Node: >= 18 (Node 20 recommended)
- npm: >= 11.5.2 (the repo pins `packageManager: npm@11.5.2` and the web Docker image installs this globally)

### Hot Reload (Backend Dev)

- Start dev profile with reload:

```
make up-dev
```

- This runs `api-dev` with `--reload` and aliases it as `api` on the network so the web container continues to proxy to `/api` without changes.

## Settings & Roster

- Settings → set “Current Week”. Automation (ingest, weather, Coach Mode) uses this.

### Roster Import (Manual ESPN)

- Use the Settings -> Roster Import UI to paste CSV or copy-paste tables exported from ESPN. Minimal columns accepted: `name, position, team, status` (start|bench|ir|fa). Unknown players are auto-added with defaults.

## Slack Alerts

- Set `SLACK_WEBHOOK_URL` in `.env`. Test via:

```
curl -X POST http://localhost:8000/api/alerts/test
```

## Ingest + Optimizer + Weather

- Update week data (CLI):

```
docker compose exec api python -m ingest.update --week 1
```

- Get optimal lineup (API):

```
curl "http://localhost:8000/api/lineup/optimal?week=1&objective=risk"
```

## ESPN Notes

- Read-only and optional. If you provide `ESPN_S2`, `SWID`, `LEAGUE_ID`, `TEAM_ID`, the app can fetch your roster read-only.
- How to get cookies: Log into ESPN in your browser, open DevTools → Application/Storage → Cookies for `fantasy.espn.com`, copy `espn_s2` and `SWID` values. `LEAGUE_ID` and `TEAM_ID` are visible in league URLs.
- Import roster via API:
  - `curl -X POST "http://localhost:8000/api/espn/import-roster?week=1"`
  - Or use the CSV import if you prefer manual.

## Tests

Run backend tests:

```
make test
```

Frontend unit tests use Vitest:

```
docker compose exec web npm test -- --run
```

## Project Layout

- `backend/`: FastAPI app, SQLModel, services (optimizer, projections, waivers, trades, schedule/weather), APScheduler.
- `ingest/`: Provider scrapers and ensemble blender CLI.
- `frontend/`: React + Vite + Tailwind UI (dark mode), responsive layout.
- `docker/`: Dockerfiles for API and Web.

## Auth (optional)

- API env:
  - `APP_PASSWORD`: shared password for login (leave empty to disable login).
  - `AUTH_SECRET`: random string to sign tokens.

## Make Targets

### Automation

- Friday job (auto): pulls FP/ESPN projections + injuries + both ADPs, blends, ensures games, fetches weather, Slack summary.
- Sunday job (auto): refreshes injuries + weather, re-optimizes lineup (risk-adjusted), Slack summary.

You can still use the Dashboard “Ingest + Blend” and Lineup “Fetch Weather” for manual updates.
- `make up` — build + start
- `make up-dev` — dev profile with API `--reload`
- `make ingest WEEK=1` — run ingest CLI
- `make test` — backend tests

## Acceptance

- Import roster CSV and compute an optimal lineup by week.
- Waiver suggestions with FAAB recommendations.
- Trade evaluator with VORP delta and fairness score.
- Slack alert posts lineup summary.
- Draft helper lists best picks by position with VORP and ADP reach (FP + ESPN).
- Docker services start cleanly; tests pass.
