"""Car service configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "car-service"
    log_level: str = "INFO"

    postgres_dsn: str = "postgresql+asyncpg://carsharing:carsharing@localhost:5432/cars_db"

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "cars_geo"

    redis_url: str = "redis://localhost:6379/0"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "car-service-group"

    host: str = "0.0.0.0"
    port: int = 8001

    model_config = {"env_prefix": "CAR_"}

settings = Settings()
