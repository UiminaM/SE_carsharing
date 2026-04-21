"""Stub authentication middleware.

In production, replace with JWT validation (e.g., python-jose or authlib).
Currently passes through all requests with a user_id header for development.
"""

from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

class AuthMiddleware(BaseHTTPMiddleware):
    SKIP_PATHS = {"/healthz", "/readyz", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        user_id = request.headers.get("X-User-Id")
        if user_id:
            request.state.user_id = user_id

        return await call_next(request)
