from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel, Column, JSON


class RosterStatus(str, Enum):
    start = "start"
    bench = "bench"
    ir = "ir"
    fa = "fa"


class Player(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    espn_id: Optional[int] = Field(default=None, index=True)
    name: str = Field(index=True)
    position: str = Field(index=True)
    team: Optional[str] = Field(default=None, index=True)
    bye_week: Optional[int] = Field(default=None)


class Roster(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id")
    status: RosterStatus
    acquisition_cost: Optional[float] = Field(default=None)
    my_team: bool = Field(default=True)


class Projection(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    week: int = Field(index=True)
    source: str = Field(index=True)
    expected: float
    stdev: Optional[float] = Field(default=None)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Injury(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    week: int = Field(index=True)
    status: str
    note: Optional[str] = Field(default=None)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ADP(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    source: str = Field(index=True)
    rank: float
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SettingsRow(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    data: dict = Field(sa_column=Column(JSON))


class LineupResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    week: int
    objective: str
    results_json: dict = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WaiverRec(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    week: int
    data: dict = Field(sa_column=Column(JSON))


class TradeEval(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    data: dict = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Game(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    week: int = Field(index=True)
    team: str = Field(index=True)
    opponent: Optional[str] = None
    home: bool = True
    kickoff_utc: Optional[datetime] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    weather: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DVP(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team: str = Field(index=True)
    position: str = Field(index=True)
    rank: Optional[int] = None  # 1 = toughest or easiest depending on convention; we'll use 1 = easiest (most points allowed)
    fp_allowed: Optional[float] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
