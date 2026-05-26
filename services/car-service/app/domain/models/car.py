
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from carsharing_common.database.postgres import Base

class CarStatus(StrEnum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"

class Car(Base):
    __tablename__ = "cars"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    brand: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    year: Mapped[int]
    license_plate: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    color: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(
        String(20), default=CarStatus.AVAILABLE, index=True
    )
    fuel_level: Mapped[float] = mapped_column(Float, default=100.0)
    mileage_km: Mapped[float] = mapped_column(Float, default=0.0)
    price_per_minute: Mapped[float] = mapped_column(Float, default=8.0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
