"""Archive service configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "archive-service"
    log_level: str = "INFO"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "archive-service-group"

    source_topics: list[str] = [
        "fleet.location.stream",
        "trip.events",
        "car.events",
        "user.events",
    ]

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "carsharing-archive"
    s3_region: str = "us-east-1"

    flush_max_records: int = 1_000
    flush_interval_seconds: float = 30.0

    host: str = "0.0.0.0"
    port: int = 8005

    model_config = {"env_prefix": "ARCHIVE_"}

settings = Settings()
