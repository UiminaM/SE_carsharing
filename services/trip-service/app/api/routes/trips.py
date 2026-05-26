
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.schemas.trip_schemas import (
    TripCompleteRequest,
    TripReserveRequest,
    TripResponse,
    TripStartRequest,
)
from app.api.dependencies.service import get_trip_service
from app.domain.services.trip_service import TripDomainService

router = APIRouter(prefix="/trips", tags=["trips"])

@router.post("/reserve", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def reserve_trip(
    req: TripReserveRequest,
    svc: TripDomainService = Depends(get_trip_service),
):
    try:
        trip = await svc.reserve(req.user_id, req.car_id, req.price_per_minute)
        return trip
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/{trip_id}/start", response_model=TripResponse)
async def start_trip(
    trip_id: str,
    req: TripStartRequest,
    svc: TripDomainService = Depends(get_trip_service),
):
    try:
        return await svc.start_trip(trip_id, req.latitude, req.longitude)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{trip_id}/complete", response_model=TripResponse)
async def complete_trip(
    trip_id: str,
    req: TripCompleteRequest,
    svc: TripDomainService = Depends(get_trip_service),
):
    try:
        return await svc.complete_trip(
            trip_id, req.latitude, req.longitude, req.distance_km
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{trip_id}/cancel", response_model=TripResponse)
async def cancel_trip(
    trip_id: str,
    svc: TripDomainService = Depends(get_trip_service),
):
    try:
        return await svc.cancel_trip(trip_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{trip_id}")
async def get_trip(
    trip_id: str,
    svc: TripDomainService = Depends(get_trip_service),
):
    trip = await svc.get_trip_with_cold_fallback(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

@router.get("/user/{user_id}", response_model=list[TripResponse])
async def list_user_trips(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    svc: TripDomainService = Depends(get_trip_service),
):
    return await svc.list_user_trips(user_id, limit=limit, offset=offset)

@router.post("/admin/retention", status_code=status.HTTP_200_OK)
async def trigger_retention(
    older_than_days: int = Query(default=180, ge=1, le=3650),
    batch_size: int = Query(default=100, ge=1, le=10_000),
    svc: TripDomainService = Depends(get_trip_service),
):
    threshold = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    deleted = await svc.retention_delete_archived(threshold, batch_size=batch_size)
    return {"deleted": deleted, "older_than": threshold.isoformat()}
