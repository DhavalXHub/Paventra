"""Application configuration loaded from environment variables."""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Paventra"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./paventra.db"

    # Auth
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth
    GOOGLE_OAUTH_ENABLED: bool = False
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

    # File storage
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]
    ALLOWED_VIDEO_TYPES: list[str] = ["video/mp4", "video/quicktime", "video/avi"]

    # CV Model — defaults keep inference off unless explicitly configured
    MODEL_ENABLED: bool = False
    MODEL_WEIGHTS_PATH: str = ""
    MODEL_CONFIDENCE_THRESHOLD: float = 0.4
    MODEL_DEVICE: str = "cpu"
    MAX_VIDEO_UPLOAD_SIZE_MB: int = 100

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    # Rate limiting & Proxy configuration
    RATE_LIMIT_REPORTS_PER_HOUR: int = 10
    BEHIND_TRUSTED_PROXY: bool = False
    REDIS_URL: Optional[str] = None

    # Analytics
    ANALYTICS_EXPORT_DIR: str = "analytics_exports"

    @field_validator("MAX_UPLOAD_SIZE_MB")
    @classmethod
    def validate_upload_size(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("MAX_UPLOAD_SIZE_MB must be between 1 and 100")
        return v

    @property
    def upload_path(self) -> Path:
        return Path(self.UPLOAD_DIR)

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def max_video_upload_bytes(self) -> int:
        return self.MAX_VIDEO_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
