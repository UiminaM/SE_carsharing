"""Async Redis client with geo and rate-limiting helpers."""

from __future__ import annotations

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

GEO_KEY = "cars:geo"
RATE_LIMIT_PREFIX = "ratelimit:"

class RedisService:
    def __init__(self, url: str) -> None:
        self._url = url
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(
            self._url,
            decode_responses=True,
            max_connections=50,
        )
        await self._client.ping()
        logger.info("redis_connected", url=self._url)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> aioredis.Redis:
        if not self._client:
            raise RuntimeError("Redis not connected")
        return self._client

    async def geo_add(self, car_id: str, lon: float, lat: float) -> None:
        await self.client.geoadd(GEO_KEY, (lon, lat, car_id))

    async def geo_remove(self, car_id: str) -> None:
        await self.client.zrem(GEO_KEY, car_id)

    async def geo_search_nearby(
        self,
        lon: float,
        lat: float,
        radius_km: float = 5.0,
        count: int = 20,
    ) -> list[dict]:
        """Return car IDs within radius sorted by distance."""
        results = await self.client.geosearch(
            GEO_KEY,
            longitude=lon,
            latitude=lat,
            radius=radius_km,
            unit="km",
            sort="ASC",
            count=count,
            withcoord=True,
            withdist=True,
        )
        cars = []
        for item in results:
            car_id = item[0] if isinstance(item, (list, tuple)) else item
            dist = item[1] if isinstance(item, (list, tuple)) and len(item) > 1 else 0
            coord = item[2] if isinstance(item, (list, tuple)) and len(item) > 2 else (0, 0)
            cars.append({
                "car_id": car_id,
                "distance_km": float(dist),
                "longitude": float(coord[0]),
                "latitude": float(coord[1]),
            })
        return cars

    async def check_rate_limit(
        self,
        client_id: str,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        """Returns (allowed: bool, remaining: int)."""
        import time

        key = f"{RATE_LIMIT_PREFIX}{client_id}"
        now = time.time()
        pipe = self.client.pipeline()
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()
        current_count = results[2]
        allowed = current_count <= max_requests
        remaining = max(0, max_requests - current_count)
        return allowed, remaining
