from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SettingsIn(BaseModel):
    data: Dict[str, Any]


class RosterImportRequest(BaseModel):
    csv: str


class LineupResponse(BaseModel):
    starters: List[Dict[str, Any]]
    bench: List[Dict[str, Any]]
    rationale: Dict[int, str]


class WhatIfRequest(BaseModel):
    week: int
    objective: str = "risk"
    overrides: Dict[int, Dict[str, float]] = {}
    lambda_risk: float = 0.35


class TradeRequest(BaseModel):
    players_in: List[int]
    players_out: List[int]


class TradeResponse(BaseModel):
    fairness: float
    delta_my: float
    delta_their: float
    rationale: str

