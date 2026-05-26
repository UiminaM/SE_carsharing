
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from carsharing_common.kafka.producer import KafkaProducerService
from carsharing_common.kafka.topics import Topics
from carsharing_common.schemas.events import (
    ChargeUserData,
    CloudEvent,
    EventType,
    TripCompletedData,
    TripReservedData,
    TripStartedData,
)
from carsharing_common.storage import S3Client

from app.domain.models.trip import Trip, TripStatus
from app.domain.repositories.archive_repository import ArchivedTripRepository
from app.domain.repositories.trip_repository import TripRepository

logger = structlog.get_logger()

class TripDomainService:
    def __init__(
        self,
        repo: TripRepository,
        kafka: KafkaProducerService,
        archive_repo: ArchivedTripRepository | None = None,
        s3: S3Client | None = None,
    ) -> None:
        self._repo = repo
        self._kafka = kafka
        self._archive_repo = archive_repo
        self._s3 = s3

    async def reserve(
        self, user_id: str, car_id: str, price_per_minute: float
    ) -> Trip:
        existing = await self._repo.get_active_by_user(user_id)
        if existing:
            raise ValueError("User already has an active trip")

        trip = Trip(
            user_id=user_id,
            car_id=car_id,
            price_per_minute=price_per_minute,
            status=TripStatus.RESERVED,
        )
        trip = await self._repo.create(trip)

        await self._kafka.publish(
            Topics.CAR_COMMANDS,
            CloudEvent(
                source="trip-service",
                type=EventType.CMD_RESERVE_CAR,
                subject=car_id,
                data={"car_id": car_id, "trip_id": trip.id, "user_id": user_id},
            ),
            key=car_id,
        )

        await self._kafka.publish(
            Topics.TRIP_EVENTS,
            CloudEvent(
                source="trip-service",
                type=EventType.TRIP_RESERVED,
                subject=trip.id,
                data=TripReservedData(
                    trip_id=trip.id, user_id=user_id, car_id=car_id
                ).model_dump(),
            ),
            key=trip.id,
        )

        logger.info("trip_reserved", trip_id=trip.id, user_id=user_id, car_id=car_id)
        return trip

    async def start_trip(
        self, trip_id: str, latitude: float, longitude: float
    ) -> Trip:
        trip = await self._repo.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found")
        if trip.status != TripStatus.RESERVED:
            raise ValueError(f"Cannot start trip in status {trip.status}")

        trip.status = TripStatus.ACTIVE
        trip.started_at = datetime.now(timezone.utc)
        trip.start_latitude = latitude
        trip.start_longitude = longitude
        trip = await self._repo.update(trip)

        await self._kafka.publish(
            Topics.TRIP_EVENTS,
            CloudEvent(
                source="trip-service",
                type=EventType.TRIP_STARTED,
                subject=trip.id,
                data=TripStartedData(
                    trip_id=trip.id,
                    user_id=trip.user_id,
                    car_id=trip.car_id,
                    start_latitude=latitude,
                    start_longitude=longitude,
                ).model_dump(),
            ),
            key=trip.id,
        )

        logger.info("trip_started", trip_id=trip.id)
        return trip

    async def complete_trip(
        self,
        trip_id: str,
        end_latitude: float,
        end_longitude: float,
        distance_km: float,
    ) -> Trip:
        trip = await self._repo.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found")
        if trip.status != TripStatus.ACTIVE:
            raise ValueError(f"Cannot complete trip in status {trip.status}")

        now = datetime.now(timezone.utc)
        duration_minutes = (now - trip.started_at).total_seconds() / 60.0
        total_cost = round(duration_minutes * trip.price_per_minute, 2)

        trip.status = TripStatus.COMPLETED
        trip.completed_at = now
        trip.end_latitude = end_latitude
        trip.end_longitude = end_longitude
        trip.distance_km = distance_km
        trip.duration_minutes = round(duration_minutes, 2)
        trip.total_cost = total_cost
        trip = await self._repo.update(trip)

        await self._kafka.publish(
            Topics.CAR_COMMANDS,
            CloudEvent(
                source="trip-service",
                type=EventType.CMD_RELEASE_CAR,
                subject=trip.car_id,
                data={
                    "car_id": trip.car_id,
                    "trip_id": trip.id,
                    "latitude": end_latitude,
                    "longitude": end_longitude,
                },
            ),
            key=trip.car_id,
        )

        await self._kafka.publish(
            Topics.USER_COMMANDS,
            CloudEvent(
                source="trip-service",
                type=EventType.CMD_CHARGE_USER,
                subject=trip.user_id,
                data=ChargeUserData(
                    user_id=trip.user_id,
                    amount=total_cost,
                    trip_id=trip.id,
                ).model_dump(),
            ),
            key=trip.user_id,
        )

        await self._kafka.publish(
            Topics.TRIP_EVENTS,
            CloudEvent(
                source="trip-service",
                type=EventType.TRIP_COMPLETED,
                subject=trip.id,
                data=TripCompletedData(
                    trip_id=trip.id,
                    user_id=trip.user_id,
                    car_id=trip.car_id,
                    distance_km=distance_km,
                    duration_minutes=round(duration_minutes, 2),
                    total_cost=total_cost,
                ).model_dump(),
            ),
            key=trip.id,
        )

        logger.info(
            "trip_completed",
            trip_id=trip.id,
            duration=round(duration_minutes, 2),
            cost=total_cost,
        )
        return trip

    async def cancel_trip(self, trip_id: str) -> Trip:
        trip = await self._repo.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found")
        if trip.status not in (TripStatus.RESERVED, TripStatus.ACTIVE):
            raise ValueError(f"Cannot cancel trip in status {trip.status}")

        trip.status = TripStatus.CANCELLED
        trip = await self._repo.update(trip)

        await self._kafka.publish(
            Topics.CAR_COMMANDS,
            CloudEvent(
                source="trip-service",
                type=EventType.CMD_RELEASE_CAR,
                subject=trip.car_id,
                data={"car_id": trip.car_id, "trip_id": trip.id},
            ),
            key=trip.car_id,
        )

        await self._kafka.publish(
            Topics.TRIP_EVENTS,
            CloudEvent(
                source="trip-service",
                type=EventType.TRIP_CANCELLED,
                subject=trip.id,
                data={"trip_id": trip.id, "user_id": trip.user_id, "car_id": trip.car_id},
            ),
            key=trip.id,
        )

        logger.info("trip_cancelled", trip_id=trip.id)
        return trip

    async def get_trip(self, trip_id: str) -> Trip | None:
        return await self._repo.get_by_id(trip_id)

    async def get_trip_with_cold_fallback(self, trip_id: str) -> dict[str, Any] | None:
        trip = await self._repo.get_by_id(trip_id)
        if trip is not None:
            return _trip_to_dict(trip, from_cold=False)

        if self._archive_repo is None or self._s3 is None:
            return None

        idx = await self._archive_repo.get(trip_id)
        if idx is None:
            return None

        try:
            blob = await self._s3.get_object(idx.s3_bucket, idx.s3_key)
        except Exception:
            logger.exception(
                "cold_read_s3_failed",
                trip_id=trip_id,
                s3_key=idx.s3_key,
            )
            return None

        from app.services.parquet_reader import parquet_find_trip
        record = parquet_find_trip(blob, trip_id)
        if record is None:
            logger.warning(
                "cold_read_trip_not_in_shard",
                trip_id=trip_id,
                s3_key=idx.s3_key,
            )
            return None
        record["_source"] = "cold"
        record["_s3_key"] = idx.s3_key
        return record

    async def retention_delete_archived(
        self, older_than: datetime, batch_size: int = 100
    ) -> int:
        if self._archive_repo is None:
            return 0

        candidates = await self._archive_repo.list_archived_before(
            older_than, limit=batch_size
        )
        deleted = 0
        for idx in candidates:
            trip = await self._repo.get_by_id(idx.trip_id)
            if trip is None:
                continue
            if trip.status not in (TripStatus.COMPLETED, TripStatus.CANCELLED):
                continue
            await self._repo.delete(trip)
            deleted += 1
        logger.info("retention_delete_run", deleted=deleted)
        return deleted

    async def list_user_trips(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[Trip]:
        return await self._repo.list_by_user(user_id, limit=limit, offset=offset)

def _trip_to_dict(trip: Trip, *, from_cold: bool) -> dict[str, Any]:
    return {
        "id": trip.id,
        "user_id": trip.user_id,
        "car_id": trip.car_id,
        "status": trip.status,
        "start_latitude": trip.start_latitude,
        "start_longitude": trip.start_longitude,
        "end_latitude": trip.end_latitude,
        "end_longitude": trip.end_longitude,
        "reserved_at": trip.reserved_at,
        "started_at": trip.started_at,
        "completed_at": trip.completed_at,
        "distance_km": trip.distance_km,
        "duration_minutes": trip.duration_minutes,
        "price_per_minute": trip.price_per_minute,
        "total_cost": trip.total_cost,
        "_source": "cold" if from_cold else "hot",
    }
