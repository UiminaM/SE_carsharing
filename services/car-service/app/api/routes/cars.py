
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.car_schemas import (
    CarCreateRequest,
    CarResponse,
    CarStatusUpdateRequest,
    LocationUpdateRequest,
    NearbyCarResponse,
    NearbySearchRequest,
)
from app.api.dependencies.service import get_car_service
from app.domain.services.car_service import CarDomainService

router = APIRouter(prefix="/cars", tags=["cars"])

@router.post("/", response_model=CarResponse, status_code=status.HTTP_201_CREATED)
async def register_car(
    req: CarCreateRequest,
    svc: CarDomainService = Depends(get_car_service),
):
    car = await svc.register_car(
        brand=req.brand,
        model=req.model,
        year=req.year,
        license_plate=req.license_plate,
        color=req.color,
        price_per_minute=req.price_per_minute,
        latitude=req.latitude,
        longitude=req.longitude,
    )
    return car

@router.get("/{car_id}", response_model=CarResponse)
async def get_car(
    car_id: str,
    svc: CarDomainService = Depends(get_car_service),
):
    car = await svc.get_car(car_id)
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    return car

@router.get("/", response_model=list[CarResponse])
async def list_available_cars(
    limit: int = 50,
    offset: int = 0,
    svc: CarDomainService = Depends(get_car_service),
):
    return await svc.list_available(limit=limit, offset=offset)

@router.patch("/{car_id}/status", response_model=CarResponse)
async def update_car_status(
    car_id: str,
    req: CarStatusUpdateRequest,
    svc: CarDomainService = Depends(get_car_service),
):
    car = await svc.change_status(car_id, req.status, req.reason)
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    return car

@router.post("/nearby", response_model=list[NearbyCarResponse])
async def search_nearby(
    req: NearbySearchRequest,
    svc: CarDomainService = Depends(get_car_service),
):
    return await svc.search_nearby(
        latitude=req.latitude,
        longitude=req.longitude,
        radius_km=req.radius_km,
        limit=req.limit,
    )

@router.put("/{car_id}/location")
async def update_location(
    car_id: str,
    req: LocationUpdateRequest,
    svc: CarDomainService = Depends(get_car_service),
):
    await svc.update_location(car_id, req.latitude, req.longitude)
    return {"status": "ok"}
