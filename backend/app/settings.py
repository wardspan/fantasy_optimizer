from __future__ import annotations

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Default to 'db' for Docker Compose; use sensible defaults if env var is unset or empty
    postgres_host: str = os.getenv("POSTGRES_HOST") or "db"
    postgres_db: str = os.getenv("POSTGRES_DB") or "fantasy"
    postgres_user: str = os.getenv("POSTGRES_USER") or "fantasy"
    postgres_password: str = os.getenv("POSTGRES_PASSWORD") or "secret"

    espn_s2: str | None = os.getenv("ESPN_S2") or None
    swid: str | None = os.getenv("SWID") or None
    league_id: str | None = os.getenv("LEAGUE_ID") or None
    team_id: str | None = os.getenv("TEAM_ID") or None

    slack_webhook_url: str | None = os.getenv("SLACK_WEBHOOK_URL") or None

    smtp_host: str | None = os.getenv("SMTP_HOST") or None
    smtp_user: str | None = os.getenv("SMTP_USER") or None
    smtp_pass: str | None = os.getenv("SMTP_PASS") or None
    smtp_from: str | None = os.getenv("SMTP_FROM") or None

    tz: str = os.getenv("TZ", "UTC")

    # Simple auth (optional)
    app_password: str | None = os.getenv("APP_PASSWORD") or None
    auth_secret: str = os.getenv("AUTH_SECRET") or "change-me-secret"

    @property
    def database_url(self) -> str:
        # Include a small connect timeout to fail fast if DNS/host is bad
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}/{self.postgres_db}?connect_timeout=5"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
