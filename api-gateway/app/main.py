
from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from carsharing_common.database.redis_client import RedisService
from carsharing_common.middleware.health import router as health_router
from carsharing_common.observability.logging import setup_logging

from app.config import settings
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware

setup_logging(settings.service_name, settings.log_level)

redis_service: RedisService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_service
    redis_service = RedisService(settings.redis_url)
    await redis_service.connect()

    yield

    await redis_service.close()
    from app.routers.proxy import _http_client
    if _http_client:
        await _http_client.aclose()

app = FastAPI(
    title="Carsharing API Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(AuthMiddleware)

app.include_router(health_router)

from app.routers.proxy import router as proxy_router

app.include_router(proxy_router, prefix="/api")

@app.middleware("http")
async def rate_limit_inline(request, call_next):
    if redis_service is None:
        return await call_next(request)

    if request.url.path in ("/healthz", "/readyz", "/docs", "/openapi.json"):
        return await call_next(request)

    from app.middleware.rate_limiter import RateLimitMiddleware

    client_id = RateLimitMiddleware._get_client_id(request)
    allowed, remaining = await redis_service.check_rate_limit(
        client_id,
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    if not allowed:
        from starlette.responses import JSONResponse

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

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
