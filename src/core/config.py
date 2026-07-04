"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "Warehouse AI ERP"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # DuckDB
    DUCKDB_DATABASE: str = "warehouse.db"
    DUCKDB_READ_ONLY: bool = False

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Security
    SECRET_KEY: str = "changeme-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"


settings = Settings()
