
from __future__ import annotations

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "user-service"
    log_level: str = "INFO"

    postgres_dsn: str = "postgresql+asyncpg://carsharing:carsharing@localhost:5432/users_db"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "user-service-group"

    host: str = "0.0.0.0"
    port: int = 8002

    model_config = {"env_prefix": "USER_"}

settings = Settings()
