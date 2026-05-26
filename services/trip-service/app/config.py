
from __future__ import annotations

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "trip-service"
    log_level: str = "INFO"

    postgres_dsn: str = "postgresql+asyncpg://carsharing:carsharing@localhost:5432/trips_db"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "trip-service-group"
    kafka_archive_consumer_group: str = "trip-service-archive-index-group"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "carsharing-archive"
    s3_region: str = "us-east-1"

    host: str = "0.0.0.0"
    port: int = 8003

    model_config = {"env_prefix": "TRIP_"}

settings = Settings()
