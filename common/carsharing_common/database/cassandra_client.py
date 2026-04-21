"""Cassandra async session wrapper using cassandra-driver."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

from cassandra.cluster import Cluster, Session
from cassandra.policies import DCAwareRoundRobinPolicy

import structlog

logger = structlog.get_logger()

_executor = ThreadPoolExecutor(max_workers=8)

class CassandraClient:
    """Thin async wrapper over cassandra-driver's synchronous Session."""

    def __init__(self, contact_points: list[str], keyspace: str, port: int = 9042) -> None:
        self._contact_points = contact_points
        self._keyspace = keyspace
        self._port = port
        self._cluster: Cluster | None = None
        self._session: Session | None = None

    async def connect(self) -> None:
        loop = asyncio.get_running_loop()
        self._cluster = Cluster(
            contact_points=self._contact_points,
            port=self._port,
            load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="datacenter1"),
        )
        self._session = await loop.run_in_executor(
            _executor,
            partial(self._cluster.connect, self._keyspace),
        )
        logger.info("cassandra_connected", keyspace=self._keyspace)

    async def execute(self, query: str, params: tuple | dict | None = None) -> Any:
        if not self._session:
            raise RuntimeError("Cassandra session not connected")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _executor,
            partial(self._session.execute, query, params),
        )

    async def close(self) -> None:
        if self._cluster:
            self._cluster.shutdown()
            logger.info("cassandra_disconnected")
