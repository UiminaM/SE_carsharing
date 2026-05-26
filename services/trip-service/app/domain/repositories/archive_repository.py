
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.archived_trip import ArchivedTripIndex

class ArchivedTripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self, trip_id: str, s3_bucket: str, s3_key: str, archived_at: datetime
    ) -> None:
        stmt = pg_insert(ArchivedTripIndex).values(
            trip_id=trip_id,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            archived_at=archived_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[ArchivedTripIndex.trip_id],
            set_={
                "s3_bucket": stmt.excluded.s3_bucket,
                "s3_key": stmt.excluded.s3_key,
                "archived_at": stmt.excluded.archived_at,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get(self, trip_id: str) -> ArchivedTripIndex | None:
        return await self._session.get(ArchivedTripIndex, trip_id)

    async def list_archived_before(
        self, before: datetime, limit: int = 100
    ) -> list[ArchivedTripIndex]:
        stmt = (
            select(ArchivedTripIndex)
            .where(ArchivedTripIndex.archived_at <= before)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
