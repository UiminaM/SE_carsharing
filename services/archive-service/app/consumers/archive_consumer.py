
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.structs import ConsumerRecord

from carsharing_common.kafka.producer import KafkaProducerService
from carsharing_common.kafka.topics import Topics
from carsharing_common.schemas.events import (
    ArchivedData,
    CloudEvent,
    EventType,
    TripArchivedData,
)
from carsharing_common.storage import S3Client

from app.services.parquet_writer import records_to_parquet_bytes

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

@dataclass
class _Buffer:
    topic: str
    partition: int
    hour_bucket: str
    records: list[dict[str, Any]] = field(default_factory=list)
    start_offset: int | None = None
    end_offset: int | None = None
    created_at: float = field(default_factory=time.monotonic)

    def add(self, offset: int, record: dict[str, Any]) -> None:
        if self.start_offset is None:
            self.start_offset = offset
        self.end_offset = offset
        self.records.append(record)

    @property
    def size(self) -> int:
        return len(self.records)

    def age_seconds(self) -> float:
        return time.monotonic() - self.created_at

class ArchiveConsumer:

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        s3: S3Client,
        producer: KafkaProducerService,
        bucket: str,
        flush_max_records: int,
        flush_interval_seconds: float,
    ) -> None:
        self._bootstrap = bootstrap_servers
        self._group_id = group_id
        self._topics = topics
        self._s3 = s3
        self._producer = producer
        self._bucket = bucket
        self._max_records = flush_max_records
        self._flush_interval = flush_interval_seconds

        self._consumer: AIOKafkaConsumer | None = None
        self._buffers: dict[tuple[str, int, str], _Buffer] = {}
        self._running = False
        self._flush_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._bootstrap,
            group_id=self._group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await self._consumer.start()
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info(
            "archive_consumer_started",
            group_id=self._group_id,
            topics=self._topics,
            bucket=self._bucket,
        )

    async def stop(self) -> None:
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush_all(reason="shutdown")
        if self._consumer:
            await self._consumer.stop()
        logger.info("archive_consumer_stopped", group_id=self._group_id)

    async def consume_loop(self) -> None:
        if not self._consumer:
            raise RuntimeError("Consumer not started")

        while self._running:
            try:
                batch = await self._consumer.getmany(timeout_ms=1000, max_records=500)
                for _tp, messages in batch.items():
                    for msg in messages:
                        await self._handle_message(msg)
                await self._maybe_flush_size()
            except Exception:
                logger.exception("archive_consume_loop_error")
                await asyncio.sleep(1)

    async def _handle_message(self, msg: ConsumerRecord) -> None:
        try:
            event = CloudEvent.model_validate(msg.value)
            record = self._flatten(event)
        except Exception:
            logger.warning(
                "archive_invalid_message",
                topic=msg.topic,
                partition=msg.partition,
                offset=msg.offset,
                raw=str(msg.value)[:200],
            )
            return

        hour_bucket = event.time.astimezone(timezone.utc).strftime("%Y/%m/%d/%H")
        key = (msg.topic, msg.partition, hour_bucket)
        buf = self._buffers.get(key)
        if buf is None:
            buf = _Buffer(topic=msg.topic, partition=msg.partition, hour_bucket=hour_bucket)
            self._buffers[key] = buf
        buf.add(msg.offset, record)

    def _flatten(self, event: CloudEvent) -> dict[str, Any]:
        return {
            "event_id": event.id,
            "event_type": str(event.type),
            "source": event.source,
            "subject": event.subject,
            "correlation_id": event.correlation_id,
            "time": event.time.astimezone(timezone.utc),
            "idempotency_key": event.idempotency_key,
            "data": json.dumps(event.data, default=str, ensure_ascii=False),
        }

    async def _periodic_flush(self) -> None:
        while self._running:
            await asyncio.sleep(min(self._flush_interval, 5.0))
            await self._flush_aged()

    async def _maybe_flush_size(self) -> None:
        to_flush = [
            k for k, b in self._buffers.items() if b.size >= self._max_records
        ]
        for k in to_flush:
            await self._flush_buffer(k, reason="size")

    async def _flush_aged(self) -> None:
        to_flush = [
            k for k, b in self._buffers.items()
            if b.size > 0 and b.age_seconds() >= self._flush_interval
        ]
        for k in to_flush:
            await self._flush_buffer(k, reason="age")

    async def _flush_all(self, *, reason: str) -> None:
        for k in list(self._buffers.keys()):
            await self._flush_buffer(k, reason=reason)

    async def _flush_buffer(
        self, key: tuple[str, int, str], *, reason: str
    ) -> None:
        buf = self._buffers.pop(key, None)
        if buf is None or buf.size == 0 or buf.end_offset is None or buf.start_offset is None:
            return

        s3_key = (
            f"{buf.topic}/{buf.hour_bucket}/"
            f"part-{buf.partition:04d}-{buf.start_offset:020d}-{buf.end_offset:020d}.parquet"
        )

        try:
            blob = records_to_parquet_bytes(buf.records)
            await self._s3.put_object(
                bucket=self._bucket,
                key=s3_key,
                body=blob,
                content_type="application/vnd.apache.parquet",
                metadata={
                    "source-topic": buf.topic,
                    "partition": str(buf.partition),
                    "start-offset": str(buf.start_offset),
                    "end-offset": str(buf.end_offset),
                    "records": str(buf.size),
                },
            )
        except Exception:
            logger.exception(
                "archive_flush_failed",
                topic=buf.topic,
                partition=buf.partition,
                s3_key=s3_key,
                reason=reason,
            )
            self._buffers[key] = buf
            return

        await self._publish_watermark(buf, s3_key)
        await self._commit_offsets(buf)
        logger.info(
            "archive_flushed",
            topic=buf.topic,
            partition=buf.partition,
            records=buf.size,
            start_offset=buf.start_offset,
            end_offset=buf.end_offset,
            s3_key=s3_key,
            reason=reason,
        )

    async def _publish_watermark(self, buf: _Buffer, s3_key: str) -> None:
        watermark = ArchivedData(
            source_topic=buf.topic,
            partition=buf.partition,
            start_offset=buf.start_offset or 0,
            end_offset=buf.end_offset or 0,
            record_count=buf.size,
            s3_bucket=self._bucket,
            s3_key=s3_key,
            watermark_ts=datetime.now(timezone.utc),
        )
        await self._producer.publish(
            Topics.ARCHIVE_EVENTS,
            CloudEvent(
                source="archive-service",
                type=EventType.ARCHIVED,
                subject=f"{buf.topic}/{buf.partition}",
                data=watermark.model_dump(mode="json"),
            ),
            key=f"{buf.topic}:{buf.partition}",
        )

        if buf.topic == Topics.TRIP_EVENTS:
            now = datetime.now(timezone.utc)
            for record in buf.records:
                if record.get("event_type") != EventType.TRIP_COMPLETED:
                    continue
                try:
                    data = json.loads(record["data"])
                    trip_id = data.get("trip_id") or record.get("subject")
                except Exception:
                    trip_id = record.get("subject")
                if not trip_id:
                    continue
                await self._producer.publish(
                    Topics.ARCHIVE_EVENTS,
                    CloudEvent(
                        source="archive-service",
                        type=EventType.TRIP_ARCHIVED,
                        subject=trip_id,
                        data=TripArchivedData(
                            trip_id=trip_id,
                            s3_bucket=self._bucket,
                            s3_key=s3_key,
                            archived_at=now,
                        ).model_dump(mode="json"),
                    ),
                    key=trip_id,
                )

    async def _commit_offsets(self, buf: _Buffer) -> None:
        if not self._consumer or buf.end_offset is None:
            return
        tp = TopicPartition(buf.topic, buf.partition)
        await self._consumer.commit({tp: buf.end_offset + 1})
