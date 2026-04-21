"""Fleet/Tracking service configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "fleet-service"
    log_level: str = "INFO"

    cassandra_hosts: str = "localhost"
    cassandra_port: int = 9042
    cassandra_keyspace: str = "fleet_tracking"

    redis_url: str = "redis://localhost:6379/0"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "fleet-service-group"

    host: str = "0.0.0.0"
    port: int = 8004

    model_config = {"env_prefix": "FLEET_"}

    @property
    def cassandra_contact_points(self) -> list[str]:
        return [h.strip() for h in self.cassandra_hosts.split(",")]

settings = Settings()
