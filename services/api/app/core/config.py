from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    app_name: str = "PYRO RENTALS"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    database_url: str = "postgresql+psycopg://pyro:pyro_dev_only@localhost:5432/pyro"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = Field(min_length=32)
    jwt_refresh_secret: str = Field(min_length=32)
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    booking_hold_minutes: int = Field(default=20, ge=5, le=60)
    cors_origins: str = "http://localhost:3000"
    payment_provider: str = "sandbox"
    payment_api_key: str = ""
    payment_secret: str = ""
    storage_bucket: str = ""
    storage_region: str = "us-east-1"
    storage_endpoint: str = ""
    storage_public_endpoint: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""

    @field_validator("app_env")
    @classmethod
    def normalize_env(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"development", "test", "staging", "production"}:
            raise ValueError("APP_ENV must be development, test, staging or production")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def validate_runtime_safety(self) -> None:
        if self.app_env == "production" and self.storage_public_endpoint and not self.storage_public_endpoint.startswith("https://"):
            raise RuntimeError("Public document storage must use HTTPS in production")
        if self.app_env == "production" and self.payment_provider == "sandbox":
            raise RuntimeError("PAYMENT_PROVIDER=sandbox is forbidden in production")
        if self.app_env == "production" and "localhost" in self.database_url:
            raise RuntimeError("Production database cannot point to localhost")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime_safety()
    return settings
