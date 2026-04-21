"""Consume archive.events watermarks and maintain archived_trips_index."""

from __future__ import annotations

from datetime import datetime

import structlog

from carsharing_common.schemas.events import CloudEvent, EventType

logger = structlog.get_logger()

async def handle_trip_archived(event: CloudEvent) -> None:
    from app.domain.repositories.archive_repository import ArchivedTripRepository
    from app.main import session_factory
    from carsharing_common.database.postgres import get_session

    data = event.data or {}
    trip_id = data.get("trip_id") or event.subject
    if not trip_id:
        logger.warning("trip_archived_missing_trip_id", event_id=event.id)
        return

    s3_bucket = data.get("s3_bucket", "")
    s3_key = data.get("s3_key", "")
    archived_at_raw = data.get("archived_at")
    archived_at = (
        datetime.fromisoformat(archived_at_raw)
        if isinstance(archived_at_raw, str)
        else datetime.utcnow()
    )

    async for session in get_session(session_factory):
        repo = ArchivedTripRepository(session)
        await repo.upsert(trip_id, s3_bucket, s3_key, archived_at)
    logger.info(
        "trip_archived_indexed",
        trip_id=trip_id,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
    )

def register_handlers(consumer) -> None:
    consumer.register_handler(EventType.TRIP_ARCHIVED, handle_trip_archived)
