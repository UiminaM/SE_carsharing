"""Index of trips that have been successfully archived to cold storage.

Populated from Kafka (``archive.events`` / TRIP_ARCHIVED watermarks emitted
by the Archive Service). Used as a safety gate before deleting rows from
``trips`` (retention worker) and as a lookup when serving cold reads.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from carsharing_common.database.postgres import Base

class ArchivedTripIndex(Base):
    __tablename__ = "archived_trips_index"

    trip_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    s3_bucket: Mapped[str] = mapped_column(String(128))
    s3_key: Mapped[str] = mapped_column(String(512))
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
