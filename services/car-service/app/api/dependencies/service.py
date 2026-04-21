"""FastAPI dependency injection for Car domain service."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.car_repository import CarRepository
from app.domain.services.car_service import CarDomainService

async def _get_session() -> AsyncGenerator[AsyncSession, None]:
    from app.main import session_factory
    from carsharing_common.database.postgres import get_session

    async for s in get_session(session_factory):
        yield s

def _get_repo(session: AsyncSession = Depends(_get_session)) -> CarRepository:
    return CarRepository(session)

async def get_car_service(
    repo: CarRepository = Depends(_get_repo),
) -> CarDomainService:
    from app.main import mongo_db, redis_service, kafka_producer

    return CarDomainService(
        repo=repo,
        mongo_db=mongo_db,
        redis=redis_service,
        kafka=kafka_producer,
    )
