from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    jwt_secret: str = Field(min_length=32)
    jwt_issuer: str = "smart-car-marketplace"
    jwt_audience: str = "marketplace-api"
    token_minutes: int = 30
    cache_ttl_seconds: int = 60
    quote_minutes: int = 10
    statistics_max_age_seconds: int = 600


@lru_cache
def get_settings() -> Settings:
    return Settings()
