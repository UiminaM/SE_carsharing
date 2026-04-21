"""FastAPI dependency injection for Fleet domain service."""

from __future__ import annotations

from app.domain.services.fleet_service import FleetDomainService

async def get_fleet_service() -> FleetDomainService:
    from app.main import tracking_repo, redis_service, kafka_producer

    return FleetDomainService(
        tracking_repo=tracking_repo,
        redis=redis_service,
        kafka=kafka_producer,
    )
