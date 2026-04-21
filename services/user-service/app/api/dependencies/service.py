"""FastAPI dependency injection for User domain service."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.user_repository import UserRepository
from app.domain.services.user_service import UserDomainService

async def _get_session() -> AsyncGenerator[AsyncSession, None]:
    from app.main import session_factory
    from carsharing_common.database.postgres import get_session

    async for s in get_session(session_factory):
        yield s

def _get_repo(session: AsyncSession = Depends(_get_session)) -> UserRepository:
    return UserRepository(session)

async def get_user_service(
    repo: UserRepository = Depends(_get_repo),
) -> UserDomainService:
    from app.main import kafka_producer

    return UserDomainService(repo=repo, kafka=kafka_producer)
