"""Kafka consumer for fleet.location.stream — ingests IoT position data."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from carsharing_common.schemas.events import CloudEvent, EventType

logger = structlog.get_logger()

async def handle_location_stream(event: CloudEvent) -> None:
    from app.main import tracking_repo, redis_service, kafka_producer
    from app.domain.services.fleet_service import FleetDomainService

    svc = FleetDomainService(tracking_repo, redis_service, kafka_producer)

    data = event.data
    car_id = data.get("car_id")
    if not car_id:
        logger.warning("location_stream_missing_car_id", event_id=event.id)
        return

    await svc.ingest_position(
        car_id=car_id,
        latitude=float(data.get("latitude", 0)),
        longitude=float(data.get("longitude", 0)),
        speed=float(data.get("speed", 0)),
        heading=float(data.get("heading", 0)),
        timestamp=datetime.fromisoformat(data["timestamp"])
        if "timestamp" in data
        else datetime.now(timezone.utc),
    )

def register_handlers(consumer) -> None:
    consumer.register_handler(
        EventType.LOCATION_BATCH_RECEIVED, handle_location_stream
    )
