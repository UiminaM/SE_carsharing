"""Reverse-proxy router that forwards requests to downstream microservices.

Aggregation endpoints combine data from multiple services when needed.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.config import settings

logger = structlog.get_logger()

router = APIRouter()

_http_client: httpx.AsyncClient | None = None

async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    return _http_client

async def _proxy(method: str, url: str, **kwargs) -> Any:
    client = await get_http_client()
    try:
        resp = await client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.RequestError as e:
        logger.error("proxy_error", url=url, error=str(e))
        raise HTTPException(status_code=503, detail="Downstream service unavailable")

@router.post("/v1/cars")
async def create_car(request: Request):
    body = await request.json()
    return await _proxy("POST", f"{settings.car_service_url}/api/v1/cars/", json=body)

@router.get("/v1/cars")
async def list_cars(limit: int = 50, offset: int = 0):
    return await _proxy(
        "GET",
        f"{settings.car_service_url}/api/v1/cars/",
        params={"limit": limit, "offset": offset},
    )

@router.get("/v1/cars/{car_id}")
async def get_car(car_id: str):
    return await _proxy("GET", f"{settings.car_service_url}/api/v1/cars/{car_id}")

@router.post("/v1/cars/nearby")
async def search_nearby(request: Request):
    body = await request.json()
    return await _proxy("POST", f"{settings.car_service_url}/api/v1/cars/nearby", json=body)

@router.post("/v1/users")
async def create_user(request: Request):
    body = await request.json()
    return await _proxy("POST", f"{settings.user_service_url}/api/v1/users/", json=body)

@router.get("/v1/users/{user_id}")
async def get_user(user_id: str):
    return await _proxy("GET", f"{settings.user_service_url}/api/v1/users/{user_id}")

@router.post("/v1/users/{user_id}/top-up")
async def top_up(user_id: str, request: Request):
    body = await request.json()
    return await _proxy(
        "POST", f"{settings.user_service_url}/api/v1/users/{user_id}/top-up", json=body
    )

@router.post("/v1/trips/reserve")
async def reserve_trip(request: Request):
    body = await request.json()
    return await _proxy("POST", f"{settings.trip_service_url}/api/v1/trips/reserve", json=body)

@router.post("/v1/trips/{trip_id}/start")
async def start_trip(trip_id: str, request: Request):
    body = await request.json()
    return await _proxy(
        "POST", f"{settings.trip_service_url}/api/v1/trips/{trip_id}/start", json=body
    )

@router.post("/v1/trips/{trip_id}/complete")
async def complete_trip(trip_id: str, request: Request):
    body = await request.json()
    return await _proxy(
        "POST", f"{settings.trip_service_url}/api/v1/trips/{trip_id}/complete", json=body
    )

@router.post("/v1/trips/{trip_id}/cancel")
async def cancel_trip(trip_id: str):
    return await _proxy(
        "POST", f"{settings.trip_service_url}/api/v1/trips/{trip_id}/cancel"
    )

@router.get("/v1/trips/{trip_id}")
async def get_trip(trip_id: str):
    return await _proxy("GET", f"{settings.trip_service_url}/api/v1/trips/{trip_id}")

@router.get("/v1/trips/user/{user_id}")
async def list_user_trips(user_id: str, limit: int = 50, offset: int = 0):
    return await _proxy(
        "GET",
        f"{settings.trip_service_url}/api/v1/trips/user/{user_id}",
        params={"limit": limit, "offset": offset},
    )

@router.post("/v1/tracking/position")
async def ingest_position(request: Request):
    body = await request.json()
    return await _proxy(
        "POST", f"{settings.fleet_service_url}/api/v1/tracking/position", json=body
    )

@router.get("/v1/tracking/{car_id}/latest")
async def get_latest_position(car_id: str):
    return await _proxy(
        "GET", f"{settings.fleet_service_url}/api/v1/tracking/{car_id}/latest"
    )

@router.get("/v1/aggregate/trip/{trip_id}")
async def aggregate_trip_info(trip_id: str):
    """Combines trip, car, and user data in a single response."""
    client = await get_http_client()

    trip = await _proxy("GET", f"{settings.trip_service_url}/api/v1/trips/{trip_id}")

    car_future = _proxy("GET", f"{settings.car_service_url}/api/v1/cars/{trip['car_id']}")
    user_future = _proxy("GET", f"{settings.user_service_url}/api/v1/users/{trip['user_id']}")

    import asyncio
    car, user = await asyncio.gather(car_future, user_future, return_exceptions=True)

    return {
        "trip": trip,
        "car": car if not isinstance(car, Exception) else None,
        "user": user if not isinstance(user, Exception) else None,
    }
