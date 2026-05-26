
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.user import PaymentMethod, User

class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_balance(self, user_id: str, new_balance: float) -> User | None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(balance=new_balance)
            .returning(User)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()

    async def add_payment_method(self, pm: PaymentMethod) -> PaymentMethod:
        self._session.add(pm)
        await self._session.flush()
        return pm

    async def get_payment_methods(self, user_id: str) -> list[PaymentMethod]:
        stmt = select(PaymentMethod).where(PaymentMethod.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
