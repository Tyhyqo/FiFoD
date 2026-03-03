from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_VALID_DB_SCHEMES = ("postgresql://", "postgresql+asyncpg://", "postgresql+aiopg://")
_VALID_HTTP_SCHEMES = ("http://", "https://")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    DB_POOL_SIZE: int = Field(10, ge=1)
    DB_MAX_OVERFLOW: int = Field(20, ge=0)
    # Время жизни соединения в пуле (сек) — защита от TCP timeout на стороне сервера
    DB_POOL_RECYCLE: int = Field(3600, ge=60)

    EXTERNAL_API_URL: str
    EXTERNAL_API_TOKEN: str
    EXTERNAL_API_RETRY_COUNT: int = Field(3, ge=1)
    EXTERNAL_API_RETRY_DELAY: float = Field(1.0, ge=0)

    HTTP_TIMEOUT_CONNECT: float = Field(5.0, gt=0)
    HTTP_TIMEOUT_READ: float = Field(10.0, gt=0)
    HTTP_TIMEOUT_WRITE: float = Field(10.0, gt=0)
    HTTP_TIMEOUT_POOL: float = Field(5.0, gt=0)
    HTTP_MAX_CONNECTIONS: int = Field(100, ge=1)
    HTTP_MAX_KEEPALIVE_CONNECTIONS: int = Field(20, ge=1)
    HTTP_KEEPALIVE_EXPIRY: float = Field(30.0, ge=0)

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, ge=1)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, ge=1)

    FILE_DIR: str = "/app/files"

    CACHE_FILES_TTL: int = Field(60, ge=1)
    CACHE_DEVICES_TTL: int = Field(30, ge=1)

    LOG_LEVEL: str = Field("INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not any(v.startswith(s) for s in _VALID_DB_SCHEMES):
            raise ValueError(
                f"DATABASE_URL must start with one of: {_VALID_DB_SCHEMES}. "
                "Example: postgresql+asyncpg://user:pass@host:5432/db"
            )
        return v

    @field_validator("EXTERNAL_API_URL")
    @classmethod
    def validate_external_api_url(cls, v: str) -> str:
        if not any(v.startswith(s) for s in _VALID_HTTP_SCHEMES):
            raise ValueError(
                "EXTERNAL_API_URL must start with http:// or https://"
            )
        return v


settings = Settings()
