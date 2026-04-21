"""Tracking repository — Cassandra time-series writes/reads."""

from __future__ import annotations

from datetime import datetime

import structlog

from carsharing_common.database.cassandra_client import CassandraClient

logger = structlog.get_logger()

CREATE_KEYSPACE_CQL = """
CREATE KEYSPACE IF NOT EXISTS fleet_tracking
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
"""

CREATE_TABLE_CQL = """
CREATE TABLE IF NOT EXISTS fleet_tracking.car_positions (
    car_id text,
    ts timestamp,
    latitude double,
    longitude double,
    speed double,
    heading double,
    PRIMARY KEY (car_id, ts)
) WITH CLUSTERING ORDER BY (ts DESC)
  AND default_time_to_live = 2592000
"""

INSERT_POSITION_CQL = """
INSERT INTO fleet_tracking.car_positions (car_id, ts, latitude, longitude, speed, heading)
VALUES (%s, %s, %s, %s, %s, %s)
"""

SELECT_HISTORY_CQL = """
SELECT car_id, ts, latitude, longitude, speed, heading
FROM fleet_tracking.car_positions
WHERE car_id = %s AND ts >= %s AND ts <= %s
ORDER BY ts DESC
LIMIT %s
"""

SELECT_LATEST_CQL = """
SELECT car_id, ts, latitude, longitude, speed, heading
FROM fleet_tracking.car_positions
WHERE car_id = %s
ORDER BY ts DESC
LIMIT 1
"""

class TrackingRepository:
    def __init__(self, client: CassandraClient) -> None:
        self._client = client

    async def init_schema(self) -> None:
        await self._client.execute(CREATE_KEYSPACE_CQL)
        await self._client.execute(CREATE_TABLE_CQL)
        logger.info("cassandra_schema_initialized")

    async def insert_position(
        self,
        car_id: str,
        timestamp: datetime,
        latitude: float,
        longitude: float,
        speed: float = 0.0,
        heading: float = 0.0,
    ) -> None:
        await self._client.execute(
            INSERT_POSITION_CQL,
            (car_id, timestamp, latitude, longitude, speed, heading),
        )

    async def get_history(
        self,
        car_id: str,
        start: datetime,
        end: datetime,
        limit: int = 1000,
    ) -> list[dict]:
        rows = await self._client.execute(
            SELECT_HISTORY_CQL, (car_id, start, end, limit)
        )
        return [
            {
                "car_id": row.car_id,
                "timestamp": row.ts,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "speed": row.speed,
                "heading": row.heading,
            }
            for row in rows
        ]

    async def get_latest_position(self, car_id: str) -> dict | None:
        rows = await self._client.execute(SELECT_LATEST_CQL, (car_id,))
        for row in rows:
            return {
                "car_id": row.car_id,
                "timestamp": row.ts,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "speed": row.speed,
                "heading": row.heading,
            }
        return None
