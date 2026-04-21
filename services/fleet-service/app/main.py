"""Fleet/Tracking service entry point."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from carsharing_common.database.cassandra_client import CassandraClient
from carsharing_common.database.redis_client import RedisService
from carsharing_common.kafka.consumer import KafkaConsumerService
from carsharing_common.kafka.producer import KafkaProducerService
from carsharing_common.kafka.topics import Topics
from carsharing_common.middleware.health import register_readiness_check, router as health_router
from carsharing_common.observability.logging import setup_logging

from app.config import settings
from app.consumers.location_consumer import register_handlers
from app.domain.repositories.tracking_repository import TrackingRepository

setup_logging(settings.service_name, settings.log_level)

tracking_repo: TrackingRepository = None
redis_service: RedisService = None
kafka_producer: KafkaProducerService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tracking_repo, redis_service, kafka_producer

    cassandra = CassandraClient(
        contact_points=settings.cassandra_contact_points,
        keyspace=settings.cassandra_keyspace,
        port=settings.cassandra_port,
    )
    await cassandra.connect()

    tracking_repo = TrackingRepository(cassandra)
    await tracking_repo.init_schema()

    redis_service = RedisService(settings.redis_url)
    await redis_service.connect()

    kafka_producer = KafkaProducerService(
        settings.kafka_bootstrap_servers, client_id="fleet-service"
    )
    await kafka_producer.start()

    consumer = KafkaConsumerService(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        topics=[Topics.FLEET_LOCATION_STREAM],
    )
    register_handlers(consumer)
    await consumer.start()
    consumer_task = asyncio.create_task(consumer.consume_loop())

    async def _check_cassandra():
        result = await cassandra.execute("SELECT now() FROM system.local")
        return result is not None

    register_readiness_check(_check_cassandra)

    yield

    consumer_task.cancel()
    await consumer.stop()
    await kafka_producer.stop()
    await redis_service.close()
    await cassandra.close()

app = FastAPI(title="Fleet/Tracking Service", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)

from app.api.routes.tracking import router as tracking_router

app.include_router(tracking_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
