"""Archive service entry point: FastAPI (healthz/readyz) + Kafka→S3 consumer."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from carsharing_common.kafka.producer import KafkaProducerService
from carsharing_common.middleware.health import (
    register_readiness_check,
    router as health_router,
)
from carsharing_common.observability.logging import setup_logging
from carsharing_common.storage import S3Client

from app.config import settings
from app.consumers.archive_consumer import ArchiveConsumer

setup_logging(settings.service_name, settings.log_level)

consumer: ArchiveConsumer | None = None
producer: KafkaProducerService | None = None
consume_task: asyncio.Task[None] | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer, producer, consume_task

    s3 = S3Client(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        region=settings.s3_region,
    )
    await s3.ensure_bucket(settings.s3_bucket)

    producer = KafkaProducerService(
        settings.kafka_bootstrap_servers, client_id="archive-service"
    )
    await producer.start()

    consumer = ArchiveConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        topics=settings.source_topics,
        s3=s3,
        producer=producer,
        bucket=settings.s3_bucket,
        flush_max_records=settings.flush_max_records,
        flush_interval_seconds=settings.flush_interval_seconds,
    )
    await consumer.start()
    consume_task = asyncio.create_task(consumer.consume_loop())

    async def _check_kafka() -> bool:
        return consume_task is not None and not consume_task.done()

    register_readiness_check(_check_kafka)

    yield

    if consume_task:
        consume_task.cancel()
        try:
            await consume_task
        except asyncio.CancelledError:
            pass
    if consumer:
        await consumer.stop()
    if producer:
        await producer.stop()

app = FastAPI(title="Archive Service", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
