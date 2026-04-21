"""User service entry point."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from carsharing_common.database.postgres import Base, create_engine, create_session_factory
from carsharing_common.kafka.consumer import KafkaConsumerService
from carsharing_common.kafka.producer import KafkaProducerService
from carsharing_common.kafka.topics import Topics
from carsharing_common.middleware.health import register_readiness_check, router as health_router
from carsharing_common.observability.logging import setup_logging

from app.config import settings
from app.consumers.user_commands_consumer import register_handlers

setup_logging(settings.service_name, settings.log_level)

session_factory: async_sessionmaker[AsyncSession] = None
kafka_producer: KafkaProducerService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global session_factory, kafka_producer

    engine = create_engine(settings.postgres_dsn)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    kafka_producer = KafkaProducerService(
        settings.kafka_bootstrap_servers, client_id="user-service"
    )
    await kafka_producer.start()

    consumer = KafkaConsumerService(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        topics=[Topics.USER_COMMANDS],
    )
    register_handlers(consumer)
    await consumer.start()
    consumer_task = asyncio.create_task(consumer.consume_loop())

    async def _check_pg():
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True

    register_readiness_check(_check_pg)

    yield

    consumer_task.cancel()
    await consumer.stop()
    await kafka_producer.stop()
    await engine.dispose()

app = FastAPI(title="User Service", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)

from app.api.routes.users import router as users_router

app.include_router(users_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
