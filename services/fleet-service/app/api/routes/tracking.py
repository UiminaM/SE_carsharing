
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.fleet_schemas import (
    HistoryRequest,
    PositionBatchRequest,
    PositionIngestRequest,
    PositionResponse,
)
from app.api.dependencies.service import get_fleet_service
from app.domain.services.fleet_service import FleetDomainService

router = APIRouter(prefix="/tracking", tags=["tracking"])

@router.post("/position")
async def ingest_position(
    req: PositionIngestRequest,
    svc: FleetDomainService = Depends(get_fleet_service),
):
    await svc.ingest_position(
        car_id=req.car_id,
        latitude=req.latitude,
        longitude=req.longitude,
        speed=req.speed,
        heading=req.heading,
        timestamp=req.timestamp,
    )
    return {"status": "ok"}

@router.post("/position/batch")
async def ingest_batch(
    req: PositionBatchRequest,
    svc: FleetDomainService = Depends(get_fleet_service),
):
    for pos in req.positions:
        await svc.ingest_position(
            car_id=pos.car_id,
            latitude=pos.latitude,
            longitude=pos.longitude,
            speed=pos.speed,
            heading=pos.heading,
            timestamp=pos.timestamp,
        )
    return {"status": "ok", "count": len(req.positions)}

@router.get("/{car_id}/latest", response_model=PositionResponse | None)
async def get_latest_position(
    car_id: str,
    svc: FleetDomainService = Depends(get_fleet_service),
):
    pos = await svc.get_latest(car_id)
    if not pos:
        raise HTTPException(status_code=404, detail="No position data for car")
    return pos

@router.post("/{car_id}/history", response_model=list[PositionResponse])
async def get_position_history(
    car_id: str,
    req: HistoryRequest,
    svc: FleetDomainService = Depends(get_fleet_service),
):
    return await svc.get_history(car_id, req.start, req.end, req.limit)
