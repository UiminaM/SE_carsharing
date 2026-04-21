"""Car domain service — business logic orchestration."""

from __future__ import annotations

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

from carsharing_common.database.redis_client import RedisService
from carsharing_common.kafka.producer import KafkaProducerService
from carsharing_common.kafka.topics import Topics
from carsharing_common.schemas.events import (
    CarLocationUpdatedData,
    CarStatusChangedData,
    CloudEvent,
    EventType,
)

from app.domain.models.car import Car, CarStatus
from app.domain.repositories.car_repository import CarRepository

logger = structlog.get_logger()

class CarDomainService:
    def __init__(
        self,
        repo: CarRepository,
        mongo_db: AsyncIOMotorDatabase,
        redis: RedisService,
        kafka: KafkaProducerService,
    ) -> None:
        self._repo = repo
        self._mongo = mongo_db
        self._redis = redis
        self._kafka = kafka

    async def register_car(
        self,
        brand: str,
        model: str,
        year: int,
        license_plate: str,
        color: str,
        price_per_minute: float,
        latitude: float,
        longitude: float,
    ) -> Car:
        car = Car(
            brand=brand,
            model=model,
            year=year,
            license_plate=license_plate,
            color=color,
            price_per_minute=price_per_minute,
        )
        car = await self._repo.create(car)

        await self._mongo.car_locations.insert_one({
            "_id": car.id,
            "location": {"type": "Point", "coordinates": [longitude, latitude]},
            "status": CarStatus.AVAILABLE,
            "updated_at": car.created_at,
        })

        await self._redis.geo_add(car.id, longitude, latitude)

        await self._kafka.publish(
            Topics.CAR_EVENTS,
            CloudEvent(
                source="car-service",
                type=EventType.CAR_REGISTERED,
                subject=car.id,
                data={"car_id": car.id, "license_plate": license_plate},
            ),
            key=car.id,
        )

        logger.info("car_registered", car_id=car.id, plate=license_plate)
        return car

    async def change_status(
        self, car_id: str, new_status: CarStatus, reason: str | None = None
    ) -> Car | None:
        car = await self._repo.get_by_id(car_id)
        if not car:
            return None

        old_status = car.status
        car = await self._repo.update_status(car_id, new_status)

        await self._mongo.car_locations.update_one(
            {"_id": car_id}, {"$set": {"status": new_status}}
        )

        if new_status == CarStatus.AVAILABLE:
            pass
        elif new_status in (CarStatus.RESERVED, CarStatus.IN_USE, CarStatus.MAINTENANCE):
            await self._redis.geo_remove(car_id)

        event_data = CarStatusChangedData(
            car_id=car_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
        )
        await self._kafka.publish(
            Topics.CAR_EVENTS,
            CloudEvent(
                source="car-service",
                type=EventType.CAR_STATUS_CHANGED,
                subject=car_id,
                data=event_data.model_dump(),
            ),
            key=car_id,
        )

        logger.info("car_status_changed", car_id=car_id, old=old_status, new=new_status)
        return car

    async def update_location(
        self, car_id: str, latitude: float, longitude: float
    ) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        await self._mongo.car_locations.update_one(
            {"_id": car_id},
            {
                "$set": {
                    "location": {"type": "Point", "coordinates": [longitude, latitude]},
                    "updated_at": now,
                }
            },
            upsert=True,
        )

        car = await self._repo.get_by_id(car_id)
        if car and car.status == CarStatus.AVAILABLE:
            await self._redis.geo_add(car_id, longitude, latitude)

        event_data = CarLocationUpdatedData(
            car_id=car_id, latitude=latitude, longitude=longitude, timestamp=now
        )
        await self._kafka.publish(
            Topics.CAR_LOCATION,
            CloudEvent(
                source="car-service",
                type=EventType.CAR_LOCATION_UPDATED,
                subject=car_id,
                data=event_data.model_dump(mode="json"),
            ),
            key=car_id,
        )

    async def search_nearby(
        self, latitude: float, longitude: float, radius_km: float = 5.0, limit: int = 20
    ) -> list[dict]:
        return await self._redis.geo_search_nearby(
            lon=longitude, lat=latitude, radius_km=radius_km, count=limit
        )

    async def get_car(self, car_id: str) -> Car | None:
        return await self._repo.get_by_id(car_id)

    async def list_available(self, limit: int = 50, offset: int = 0) -> list[Car]:
        return await self._repo.list_available(limit=limit, offset=offset)
