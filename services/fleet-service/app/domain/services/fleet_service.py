
from __future__ import annotations

from datetime import datetime, timezone

import structlog

from carsharing_common.database.redis_client import RedisService
from carsharing_common.kafka.producer import KafkaProducerService
from carsharing_common.kafka.topics import Topics
from carsharing_common.schemas.events import (
    CarLocationUpdatedData,
    CloudEvent,
    EventType,
)

from app.domain.repositories.tracking_repository import TrackingRepository

logger = structlog.get_logger()

class FleetDomainService:
    def __init__(
        self,
        tracking_repo: TrackingRepository,
        redis: RedisService,
        kafka: KafkaProducerService,
    ) -> None:
        self._tracking = tracking_repo
        self._redis = redis
        self._kafka = kafka

    async def ingest_position(
        self,
        car_id: str,
        latitude: float,
        longitude: float,
        speed: float = 0.0,
        heading: float = 0.0,
        timestamp: datetime | None = None,
    ) -> None:
        ts = timestamp or datetime.now(timezone.utc)

        await self._tracking.insert_position(
            car_id=car_id,
            timestamp=ts,
            latitude=latitude,
            longitude=longitude,
            speed=speed,
            heading=heading,
        )

        await self._redis.geo_add(car_id, longitude, latitude)

        event_data = CarLocationUpdatedData(
            car_id=car_id,
            latitude=latitude,
            longitude=longitude,
            timestamp=ts,
        )
        await self._kafka.publish(
            Topics.CAR_LOCATION,
            CloudEvent(
                source="fleet-service",
                type=EventType.CAR_LOCATION_UPDATED,
                subject=car_id,
                data=event_data.model_dump(mode="json"),
            ),
            key=car_id,
        )

    async def get_history(
        self, car_id: str, start: datetime, end: datetime, limit: int = 1000
    ) -> list[dict]:
        return await self._tracking.get_history(car_id, start, end, limit)

    async def get_latest(self, car_id: str) -> dict | None:
        return await self._tracking.get_latest_position(car_id)
