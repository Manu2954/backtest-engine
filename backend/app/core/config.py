from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    database_url: str = "postgresql+asyncpg://backtest:backtest@localhost:5432/backtest"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_backend_url: str = "redis://localhost:6379/2"
    ohlcv_cache_ttl_seconds: int = 60 * 60 * 24
    cors_origins: str = "http://localhost:5173"
    rate_limit_per_minute: int = 100
    rate_limit_expensive_per_minute: int = 10


settings = Settings()
