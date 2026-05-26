
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.archive_repository import ArchivedTripRepository
from app.domain.repositories.trip_repository import TripRepository
from app.domain.services.trip_service import TripDomainService

async def _get_session() -> AsyncGenerator[AsyncSession, None]:
    from app.main import session_factory
    from carsharing_common.database.postgres import get_session

    async for s in get_session(session_factory):
        yield s

def _get_repo(session: AsyncSession = Depends(_get_session)) -> TripRepository:
    return TripRepository(session)

def _get_archive_repo(
    session: AsyncSession = Depends(_get_session),
) -> ArchivedTripRepository:
    return ArchivedTripRepository(session)

async def get_trip_service(
    repo: TripRepository = Depends(_get_repo),
    archive_repo: ArchivedTripRepository = Depends(_get_archive_repo),
) -> TripDomainService:
    from app.main import kafka_producer, s3_client

    return TripDomainService(
        repo=repo,
        kafka=kafka_producer,
        archive_repo=archive_repo,
        s3=s3_client,
    )
