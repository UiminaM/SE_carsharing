
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
from carsharing_common.storage import S3Client

from app.config import settings
from app.domain.models import archived_trip as _archived_trip_model
from app.domain.models import trip as _trip_model

setup_logging(settings.service_name, settings.log_level)

session_factory: async_sessionmaker[AsyncSession] = None
kafka_producer: KafkaProducerService = None
s3_client: S3Client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global session_factory, kafka_producer, s3_client

    engine = create_engine(settings.postgres_dsn)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    kafka_producer = KafkaProducerService(
        settings.kafka_bootstrap_servers, client_id="trip-service"
    )
    await kafka_producer.start()

    s3_client = S3Client(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        region=settings.s3_region,
    )

    from app.consumers.archive_events_consumer import register_handlers

    archive_consumer = KafkaConsumerService(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_archive_consumer_group,
        topics=[Topics.ARCHIVE_EVENTS],
    )
    register_handlers(archive_consumer)
    await archive_consumer.start()
    archive_task = asyncio.create_task(archive_consumer.consume_loop())

    async def _check_pg():
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True

    register_readiness_check(_check_pg)

    yield

    archive_task.cancel()
    try:
        await archive_task
    except asyncio.CancelledError:
        pass
    await archive_consumer.stop()
    await kafka_producer.stop()
    await engine.dispose()

app = FastAPI(title="Trip Service", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)

from app.api.routes.trips import router as trips_router

app.include_router(trips_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
