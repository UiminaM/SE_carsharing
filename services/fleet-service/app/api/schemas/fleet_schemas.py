"""Pydantic v2 schemas for Fleet/Tracking API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

class PositionIngestRequest(BaseModel):
    car_id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed: float = Field(default=0.0, ge=0)
    heading: float = Field(default=0.0, ge=0, le=360)
    timestamp: datetime | None = None

class PositionBatchRequest(BaseModel):
    positions: list[PositionIngestRequest] = Field(max_length=100)

class PositionResponse(BaseModel):
    car_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    speed: float
    heading: float

class HistoryRequest(BaseModel):
    start: datetime
    end: datetime
    limit: int = Field(default=1000, gt=0, le=10000)
