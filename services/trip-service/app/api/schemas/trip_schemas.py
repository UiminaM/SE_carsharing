"""Pydantic v2 schemas for Trip API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models.trip import TripStatus

class TripReserveRequest(BaseModel):
    user_id: str
    car_id: str
    price_per_minute: float = Field(gt=0)

class TripStartRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class TripCompleteRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    distance_km: float = Field(ge=0)

class TripResponse(BaseModel):
    id: str
    user_id: str
    car_id: str
    status: TripStatus
    start_latitude: float | None
    start_longitude: float | None
    end_latitude: float | None
    end_longitude: float | None
    reserved_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    distance_km: float | None
    duration_minutes: float | None
    price_per_minute: float
    total_cost: float | None

    model_config = {"from_attributes": True}
