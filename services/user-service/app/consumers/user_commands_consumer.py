"""Kafka consumer for user commands (e.g., CMD_CHARGE_USER from Trip Service)."""

from __future__ import annotations

import structlog

from carsharing_common.schemas.events import CloudEvent, EventType

logger = structlog.get_logger()

async def handle_charge_user(event: CloudEvent) -> None:
    from app.main import session_factory, kafka_producer
    from carsharing_common.database.postgres import get_session
    from app.domain.repositories.user_repository import UserRepository
    from app.domain.services.user_service import UserDomainService

    user_id = event.data.get("user_id")
    amount = event.data.get("amount")
    trip_id = event.data.get("trip_id")

    if not user_id or amount is None:
        logger.warning("charge_user_missing_fields", event_id=event.id)
        return

    async for session in get_session(session_factory):
        repo = UserRepository(session)
        svc = UserDomainService(repo, kafka_producer)
        try:
            await svc.charge_user(user_id, float(amount), reason=f"trip:{trip_id}")
            logger.info("user_charged_via_command", user_id=user_id, amount=amount)
        except ValueError as e:
            logger.error("charge_failed", user_id=user_id, error=str(e))

def register_handlers(consumer) -> None:
    consumer.register_handler(EventType.CMD_CHARGE_USER, handle_charge_user)
