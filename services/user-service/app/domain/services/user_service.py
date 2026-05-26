
from __future__ import annotations

import hashlib

import structlog

from carsharing_common.kafka.producer import KafkaProducerService
from carsharing_common.kafka.topics import Topics
from carsharing_common.schemas.events import (
    CloudEvent,
    EventType,
    UserBalanceChangedData,
)

from app.domain.models.user import PaymentMethod, User
from app.domain.repositories.user_repository import UserRepository

logger = structlog.get_logger()

class UserDomainService:
    def __init__(self, repo: UserRepository, kafka: KafkaProducerService) -> None:
        self._repo = repo
        self._kafka = kafka

    async def register_user(
        self,
        email: str,
        phone: str,
        first_name: str,
        last_name: str,
        password: str,
    ) -> User:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user = User(
            email=email,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash,
        )
        user = await self._repo.create(user)

        await self._kafka.publish(
            Topics.USER_EVENTS,
            CloudEvent(
                source="user-service",
                type=EventType.USER_REGISTERED,
                subject=user.id,
                data={"user_id": user.id, "email": email},
            ),
            key=user.id,
        )

        logger.info("user_registered", user_id=user.id, email=email)
        return user

    async def get_user(self, user_id: str) -> User | None:
        return await self._repo.get_by_id(user_id)

    async def charge_user(
        self, user_id: str, amount: float, reason: str = "trip_payment"
    ) -> User | None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            return None

        old_balance = user.balance
        new_balance = old_balance - amount
        if new_balance < 0:
            logger.warning("insufficient_balance", user_id=user_id, balance=old_balance, amount=amount)
            raise ValueError(f"Insufficient balance: {old_balance} < {amount}")

        user = await self._repo.update_balance(user_id, new_balance)

        event_data = UserBalanceChangedData(
            user_id=user_id,
            old_balance=old_balance,
            new_balance=new_balance,
            change_amount=-amount,
            reason=reason,
        )
        await self._kafka.publish(
            Topics.USER_EVENTS,
            CloudEvent(
                source="user-service",
                type=EventType.USER_BALANCE_CHANGED,
                subject=user_id,
                data=event_data.model_dump(),
            ),
            key=user_id,
        )

        logger.info("user_charged", user_id=user_id, amount=amount, new_balance=new_balance)
        return user

    async def top_up_balance(self, user_id: str, amount: float) -> User | None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            return None

        old_balance = user.balance
        new_balance = old_balance + amount
        user = await self._repo.update_balance(user_id, new_balance)

        event_data = UserBalanceChangedData(
            user_id=user_id,
            old_balance=old_balance,
            new_balance=new_balance,
            change_amount=amount,
            reason="top_up",
        )
        await self._kafka.publish(
            Topics.USER_EVENTS,
            CloudEvent(
                source="user-service",
                type=EventType.USER_BALANCE_CHANGED,
                subject=user_id,
                data=event_data.model_dump(),
            ),
            key=user_id,
        )
        return user

    async def add_payment_method(
        self,
        user_id: str,
        method_type: str,
        token: str,
        card_last4: str | None = None,
    ) -> PaymentMethod:
        pm = PaymentMethod(
            user_id=user_id,
            method_type=method_type,
            token=token,
            card_last4=card_last4,
        )
        return await self._repo.add_payment_method(pm)
