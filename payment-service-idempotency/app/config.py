from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    environment: str = "development"
    idempotency_key_ttl: int = 86400  # 24 hours in seconds

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
