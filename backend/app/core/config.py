from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "dev-only-change-this-secret-before-deployment"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Nabz Learning API"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://nabz:nabz_dev_only@localhost:5432/nabz_learning"
    cors_origins: list[str] = ["http://localhost:3000"]
    jwt_secret_key: str = Field(default=DEFAULT_JWT_SECRET, min_length=32)
    jwt_access_token_minutes: int = Field(default=30, ge=5, le=1440)
    jwt_issuer: str = "nabz-learning"

    @model_validator(mode="after")
    def require_non_default_secret_in_production(self) -> "Settings":
        if (
            self.app_env.casefold() in {"prod", "production"}
            and self.jwt_secret_key == DEFAULT_JWT_SECRET
        ):
            raise ValueError("JWT_SECRET_KEY must be replaced before production deployment.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
