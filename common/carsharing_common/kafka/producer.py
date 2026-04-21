"""Async Kafka producer with outbox-style reliability guarantees."""

from __future__ import annotations

import json
import logging
from typing import Any

import structlog
from aiokafka import AIOKafkaProducer

from carsharing_common.schemas.events import CloudEvent

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

class KafkaProducerService:
    """Wraps AIOKafkaProducer with structured logging and serialization."""

    def __init__(self, bootstrap_servers: str, client_id: str = "carsharing") -> None:
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._client_id,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
        )
        await self._producer.start()
        logger.info("kafka_producer_started", bootstrap=self._bootstrap_servers)

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            logger.info("kafka_producer_stopped")

    async def publish(
        self,
        topic: str,
        event: CloudEvent,
        key: str | None = None,
    ) -> None:
        if not self._producer:
            raise RuntimeError("Producer not started")

        partition_key = key or event.subject or event.id
        await self._producer.send_and_wait(
            topic=topic,
            value=event.model_dump(mode="json"),
            key=partition_key,
        )
        logger.info(
            "event_published",
            topic=topic,
            event_type=event.type,
            event_id=event.id,
            correlation_id=event.correlation_id,
        )

    async def publish_raw(
        self,
        topic: str,
        value: dict[str, Any],
        key: str | None = None,
    ) -> None:
        if not self._producer:
            raise RuntimeError("Producer not started")
        await self._producer.send_and_wait(topic=topic, value=value, key=key)
