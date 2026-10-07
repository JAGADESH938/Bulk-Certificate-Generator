from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@db:5432/certificate_db"
    STORAGE_PATH: str = "storage/certificates"
    MAX_RECIPIENTS_PER_JOB: int = 1000
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "Bulk Certificate Generator"
    API_V1_PREFIX: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def storage_dir(self) -> Path:
        """Resolve storage path to an absolute Path object."""
        return Path(self.STORAGE_PATH).resolve()


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
