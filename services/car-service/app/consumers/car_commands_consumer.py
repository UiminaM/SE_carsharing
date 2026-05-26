
from __future__ import annotations

import structlog

from carsharing_common.schemas.events import CloudEvent, EventType

from app.domain.models.car import CarStatus

logger = structlog.get_logger()

async def handle_reserve_car(event: CloudEvent) -> None:
    from app.main import session_factory, mongo_db, redis_service, kafka_producer
    from carsharing_common.database.postgres import get_session
    from app.domain.repositories.car_repository import CarRepository
    from app.domain.services.car_service import CarDomainService

    async for session in get_session(session_factory):
        repo = CarRepository(session)
        svc = CarDomainService(repo, mongo_db, redis_service, kafka_producer)
        car_id = event.data.get("car_id")
        if not car_id:
            logger.warning("reserve_car_missing_car_id", event_id=event.id)
            return
        await svc.change_status(car_id, CarStatus.RESERVED, reason="trip_reservation")
        logger.info("car_reserved_via_command", car_id=car_id)

async def handle_release_car(event: CloudEvent) -> None:
    from app.main import session_factory, mongo_db, redis_service, kafka_producer
    from carsharing_common.database.postgres import get_session
    from app.domain.repositories.car_repository import CarRepository
    from app.domain.services.car_service import CarDomainService

    async for session in get_session(session_factory):
        repo = CarRepository(session)
        svc = CarDomainService(repo, mongo_db, redis_service, kafka_producer)
        car_id = event.data.get("car_id")
        if not car_id:
            logger.warning("release_car_missing_car_id", event_id=event.id)
            return

        lat = event.data.get("latitude")
        lon = event.data.get("longitude")
        if lat is not None and lon is not None:
            await svc.update_location(car_id, lat, lon)

        await svc.change_status(car_id, CarStatus.AVAILABLE, reason="trip_completed")
        logger.info("car_released_via_command", car_id=car_id)

def register_handlers(consumer) -> None:
    consumer.register_handler(EventType.CMD_RESERVE_CAR, handle_reserve_car)
    consumer.register_handler(EventType.CMD_RELEASE_CAR, handle_release_car)
