from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    # Application
    app_name: str = "FleetFlow API"
    app_version: str = "0.1.0"
    debug: bool = False
    api_key: str = ""
    environment: str = "development"  # development, staging, production
    
    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "fleetflow"
    postgres_password: str = "fleetflow_dev"
    postgres_db: str = "fleetflow"
    
    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def sync_database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # TimescaleDB
    timescale_host: str = "localhost"
    timescale_port: int = 5433
    timescale_db: str = "timescale"
    
    @property
    def timescale_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.timescale_host}:{self.timescale_port}/{self.timescale_db}"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "fleetflow-api"
    
    # External APIs
    osrm_api_url: str = "http://router.project-osrm.org"
    tomtom_api_key: str = ""
    openweathermap_api_key: str = ""
    
    # Feature Flags
    enable_mock_data: bool = True
    enable_websocket: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
