from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="secrets/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env
    )

    # Application Settings
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    # Security Settings
    secret_key: SecretStr = Field(
        default="changeme-insecure-secret-key",
        description="Secret key for signing tokens (CHANGE IN PRODUCTION!)",
    )
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins",
    )

    # Rate Limiting Settings
    rate_limit_requests: int = Field(
        default=100,
        description="Maximum requests per window",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        description="Rate limit window duration in seconds",
    )
    rate_limit_exclude_paths: list[str] = Field(
        default=["/health"],
        description="Paths excluded from rate limiting",
    )

    # Database Settings
    database_url: str = Field(
        description="Database connection URL",
    )

    # Redis Settings (example)
    # redis_host: str = Field(
    #     default="localhost",
    #     description="Redis host",
    # )
    # redis_port: int = Field(
    #     default=6379,
    #     description="Redis port",
    # )
    # redis_password: SecretStr | None = Field(
    #     default=None,
    #     description="Redis password",
    # )

    # Feature Flags (example)
    # enable_metrics: bool = Field(
    #     default=True,
    #     description="Enable metrics collection",
    # )

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
