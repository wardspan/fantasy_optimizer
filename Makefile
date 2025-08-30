SHELL := /bin/bash

.PHONY: up down logs ingest test fmt

up:
	docker compose up --build -d

up-dev:
	docker compose --profile dev up --build -d api-dev web db

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

ingest:
	@if [ -z "$(WEEK)" ]; then echo "Usage: make ingest WEEK=1"; exit 1; fi
	docker compose exec api python -m ingest.update --week $(WEEK)

test:
	docker compose exec api pytest -q

fmt:
	docker compose exec api ruff check --fix backend || true
	docker compose exec api black backend || true
