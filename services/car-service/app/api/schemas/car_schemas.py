"""Pydantic v2 request/response schemas for Car API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models.car import CarStatus

class CarCreateRequest(BaseModel):
    brand: str = Field(max_length=100)
    model: str = Field(max_length=100)
    year: int = Field(ge=2000, le=2030)
    license_plate: str = Field(max_length=20)
    color: str = Field(max_length=50)
    price_per_minute: float = Field(gt=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class CarResponse(BaseModel):
    id: str
    brand: str
    model: str
    year: int
    license_plate: str
    color: str
    status: CarStatus
    fuel_level: float
    mileage_km: float
    price_per_minute: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class CarStatusUpdateRequest(BaseModel):
    status: CarStatus
    reason: str | None = None

class NearbySearchRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=5.0, gt=0, le=50)
    limit: int = Field(default=20, gt=0, le=100)

class NearbyCarResponse(BaseModel):
    car_id: str
    distance_km: float
    longitude: float
    latitude: float

class LocationUpdateRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
