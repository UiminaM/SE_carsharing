"""API Gateway configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "api-gateway"
    log_level: str = "INFO"

    redis_url: str = "redis://localhost:6379/0"

    car_service_url: str = "http://car-service:8001"
    user_service_url: str = "http://user-service:8002"
    trip_service_url: str = "http://trip-service:8003"
    fleet_service_url: str = "http://fleet-service:8004"

    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "GW_"}

settings = Settings()
