"""Kafka event contracts shared across all services.

Every Kafka message MUST use one of these envelope schemas.
Commands represent intent (imperative), Events represent facts (past tense).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

class EventType(StrEnum):
    CAR_REGISTERED = "car.registered"
    CAR_STATUS_CHANGED = "car.status_changed"
    CAR_LOCATION_UPDATED = "car.location_updated"

    USER_REGISTERED = "user.registered"
    USER_BALANCE_CHANGED = "user.balance_changed"

    TRIP_RESERVED = "trip.reserved"
    TRIP_STARTED = "trip.started"
    TRIP_COMPLETED = "trip.completed"
    TRIP_CANCELLED = "trip.cancelled"

    LOCATION_BATCH_RECEIVED = "fleet.location_batch_received"

    CMD_RESERVE_CAR = "cmd.reserve_car"
    CMD_RELEASE_CAR = "cmd.release_car"
    CMD_CHARGE_USER = "cmd.charge_user"
    CMD_UPDATE_CAR_STATUS = "cmd.update_car_status"

    ARCHIVED = "archive.archived"
    TRIP_ARCHIVED = "archive.trip_archived"

class CloudEvent(BaseModel):
    """CloudEvents-inspired envelope for all Kafka messages."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str = Field(description="Originating service, e.g. 'trip-service'")
    type: EventType
    time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    subject: str | None = Field(default=None, description="Aggregate ID")
    correlation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="End-to-end tracing correlation",
    )
    data: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Consumer-side dedup key",
    )

class CarStatusChangedData(BaseModel):
    car_id: str
    old_status: str
    new_status: str
    reason: str | None = None

class CarLocationUpdatedData(BaseModel):
    car_id: str
    latitude: float
    longitude: float
    timestamp: datetime

class TripReservedData(BaseModel):
    trip_id: str
    user_id: str
    car_id: str

class TripStartedData(BaseModel):
    trip_id: str
    user_id: str
    car_id: str
    start_latitude: float
    start_longitude: float

class TripCompletedData(BaseModel):
    trip_id: str
    user_id: str
    car_id: str
    distance_km: float
    duration_minutes: float
    total_cost: float

class ChargeUserData(BaseModel):
    user_id: str
    amount: float
    trip_id: str
    reason: str = "trip_payment"

class UserBalanceChangedData(BaseModel):
    user_id: str
    old_balance: float
    new_balance: float
    change_amount: float
    reason: str

class ArchivedData(BaseModel):
    """Watermark: batch of messages from a Kafka partition was uploaded to S3."""

    source_topic: str
    partition: int
    start_offset: int
    end_offset: int
    record_count: int
    s3_bucket: str
    s3_key: str
    watermark_ts: datetime

class TripArchivedData(BaseModel):
    """Per-trip watermark — consumed by Trip Service to update archived_trips_index."""

    trip_id: str
    s3_bucket: str
    s3_key: str
    archived_at: datetime
