
from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from carsharing_common.database.redis_client import RedisService

from app.config import settings

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis: RedisService) -> None:
        super().__init__(app)
        self._redis = redis

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in ("/healthz", "/readyz"):
            return await call_next(request)

        client_id = self._get_client_id(request)
        allowed, remaining = await self._redis.check_rate_limit(
            client_id,
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "X-RateLimit-Limit": str(settings.rate_limit_requests),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(settings.rate_limit_window_seconds),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    @staticmethod
    def _get_client_id(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        auth = request.headers.get("Authorization")
        if auth:
            return f"auth:{auth[:20]}"

        return request.client.host if request.client else "unknown"
