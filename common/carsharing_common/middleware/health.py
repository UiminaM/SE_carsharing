"""Healthcheck endpoints reusable across all services."""

from __future__ import annotations

from fastapi import APIRouter, Response

router = APIRouter(tags=["health"])

_readiness_checks: list = []

def register_readiness_check(check_fn):
    _readiness_checks.append(check_fn)

@router.get("/healthz")
async def liveness():
    return {"status": "alive"}

@router.get("/readyz")
async def readiness():
    for check in _readiness_checks:
        try:
            ok = await check()
            if not ok:
                return Response(status_code=503, content='{"status": "not ready"}')
        except Exception:
            return Response(status_code=503, content='{"status": "not ready"}')
    return {"status": "ready"}
