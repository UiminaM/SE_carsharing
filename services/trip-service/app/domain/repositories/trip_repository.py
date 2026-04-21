"""Trip repository — PostgreSQL operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.trip import Trip, TripStatus

class TripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, trip: Trip) -> Trip:
        self._session.add(trip)
        await self._session.flush()
        return trip

    async def get_by_id(self, trip_id: str) -> Trip | None:
        return await self._session.get(Trip, trip_id)

    async def update(self, trip: Trip) -> Trip:
        await self._session.merge(trip)
        await self._session.flush()
        return trip

    async def get_active_by_user(self, user_id: str) -> Trip | None:
        stmt = select(Trip).where(
            Trip.user_id == user_id,
            Trip.status.in_([TripStatus.RESERVED, TripStatus.ACTIVE]),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[Trip]:
        stmt = (
            select(Trip)
            .where(Trip.user_id == user_id)
            .order_by(Trip.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, trip: Trip) -> None:
        await self._session.delete(trip)
        await self._session.flush()
