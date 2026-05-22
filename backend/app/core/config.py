from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "ProxyOps"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    POSTGRES_USER: str = "proxyops"
    POSTGRES_PASSWORD: str = "proxyops"
    POSTGRES_DB: str = "proxyops"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    ALGORITHM: str = "HS256"

    # Comma-separated list of allowed CORS origins. Parsed lazily into `cors_origins`.
    BACKEND_CORS_ORIGINS: str = ""

    FIRST_ADMIN_EMAIL: str = "admin@proxyops.io"
    FIRST_ADMIN_PASSWORD: str = "changeme"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
