"""Car repository — PostgreSQL operations."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.car import Car, CarStatus

class CarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, car: Car) -> Car:
        self._session.add(car)
        await self._session.flush()
        return car

    async def get_by_id(self, car_id: str) -> Car | None:
        return await self._session.get(Car, car_id)

    async def get_by_license_plate(self, plate: str) -> Car | None:
        stmt = select(Car).where(Car.license_plate == plate)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_available(self, limit: int = 50, offset: int = 0) -> list[Car]:
        stmt = (
            select(Car)
            .where(Car.status == CarStatus.AVAILABLE)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self, car_id: str, new_status: CarStatus
    ) -> Car | None:
        stmt = (
            update(Car)
            .where(Car.id == car_id)
            .values(status=new_status)
            .returning(Car)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Car]:
        stmt = select(Car).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
