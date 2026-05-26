
from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from carsharing_common.schemas.events import CloudEvent

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

EventHandler = Callable[[CloudEvent], Coroutine[Any, Any, None]]

class IdempotencyStore:

    def __init__(self, max_size: int = 100_000) -> None:
        self._seen: set[str] = set()
        self._max_size = max_size

    async def is_processed(self, key: str) -> bool:
        return key in self._seen

    async def mark_processed(self, key: str) -> None:
        if len(self._seen) >= self._max_size:
            self._seen.clear()
        self._seen.add(key)

class KafkaConsumerService:

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        max_retries: int = 3,
        dlt_suffix: str = ".dlt",
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._topics = topics
        self._max_retries = max_retries
        self._dlt_suffix = dlt_suffix
        self._handlers: dict[str, EventHandler] = {}
        self._idempotency = IdempotencyStore()
        self._consumer: AIOKafkaConsumer | None = None
        self._dlt_producer: AIOKafkaProducer | None = None
        self._running = False

    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type] = handler

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        self._dlt_producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self._consumer.start()
        await self._dlt_producer.start()
        self._running = True
        logger.info(
            "kafka_consumer_started",
            group_id=self._group_id,
            topics=self._topics,
        )

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
        if self._dlt_producer:
            await self._dlt_producer.stop()
        logger.info("kafka_consumer_stopped", group_id=self._group_id)

    async def consume_loop(self) -> None:
        if not self._consumer:
            raise RuntimeError("Consumer not started")

        while self._running:
            try:
                batch = await self._consumer.getmany(timeout_ms=1000, max_records=50)
                for _tp, messages in batch.items():
                    for msg in messages:
                        await self._process_message(msg)
                await self._consumer.commit()
            except Exception:
                logger.exception("consumer_loop_error")
                await asyncio.sleep(1)

    async def _process_message(self, msg: Any) -> None:
        try:
            event = CloudEvent.model_validate(msg.value)
        except Exception:
            logger.warning("invalid_message_format", raw=str(msg.value)[:200])
            return

        if await self._idempotency.is_processed(event.idempotency_key):
            logger.debug("duplicate_event_skipped", event_id=event.id)
            return

        handler = self._handlers.get(event.type)
        if not handler:
            logger.debug("no_handler_for_event", event_type=event.type)
            return

        for attempt in range(1, self._max_retries + 1):
            try:
                await handler(event)
                await self._idempotency.mark_processed(event.idempotency_key)
                logger.info(
                    "event_processed",
                    event_type=event.type,
                    event_id=event.id,
                    attempt=attempt,
                )
                return
            except Exception:
                logger.warning(
                    "event_processing_failed",
                    event_type=event.type,
                    event_id=event.id,
                    attempt=attempt,
                    exc_info=True,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(2**attempt)

        await self._send_to_dlt(msg, event)

    async def _send_to_dlt(self, original_msg: Any, event: CloudEvent) -> None:
        dlt_topic = original_msg.topic + self._dlt_suffix
        try:
            if self._dlt_producer:
                await self._dlt_producer.send_and_wait(
                    topic=dlt_topic,
                    value=event.model_dump(mode="json"),
                )
            logger.error(
                "event_sent_to_dlt",
                dlt_topic=dlt_topic,
                event_id=event.id,
                event_type=event.type,
            )
        except Exception:
            logger.exception("dlt_send_failed", event_id=event.id)
