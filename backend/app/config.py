# ============================================================
# SignAI_OS — Centralized Configuration
#
# Uses Pydantic BaseSettings for validated, type-safe config
# with automatic .env loading.
# ============================================================

import logging
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate .env in the backend root directory
_backend_root = Path(__file__).resolve().parent.parent
_env_path = _backend_root / ".env"


class Settings(BaseSettings):
    """
    Application-wide settings.
    Reads from environment variables with sensible defaults.
    Pydantic validates types and handles .env loading automatically.
    """

    model_config = SettingsConfigDict(
        env_file=str(_env_path),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Server ───────────────────────────────────────────────
    ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # ── Version ──────────────────────────────────────────────
    APP_VERSION: str = "2.3.0"
    APP_NAME: str = "SignAI_OS"

    # ── CORS ─────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # ── OpenAI ───────────────────────────────────────────────
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Auth ─────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "super-secret-default-key-please-change"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: Optional[str] = None

    # ── Rate Limiting ────────────────────────────────────────
    WS_MAX_MESSAGES_PER_SECOND: int = 20
    REST_MAX_REQUESTS_PER_MINUTE: int = 60

    # ── Aliases for env var names ────────────────────────────
    WS_RATE_LIMIT: Optional[int] = None      # Maps to WS_MAX_MESSAGES_PER_SECOND
    REST_RATE_LIMIT: Optional[int] = None     # Maps to REST_MAX_REQUESTS_PER_MINUTE

    # ── Analytics ────────────────────────────────────────────
    ANALYTICS_MAX_LATENCY_SAMPLES: int = 500

    # ── Logging ──────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def set_debug(cls, v, info):
        """Auto-set DEBUG based on ENV if not explicitly provided."""
        if isinstance(v, bool):
            return v
        # If ENV is set in the values dict, derive DEBUG from it
        env = info.data.get("ENV", "development")
        return env == "development"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_origins(cls, v, info):
        """Ensure FRONTEND_URL is always in the allowed origins."""
        if isinstance(v, str):
            origins = [o.strip() for o in v.split(",")]
        else:
            origins = list(v) if v else []
        frontend_url = info.data.get("FRONTEND_URL", "http://localhost:3000")
        if frontend_url not in origins:
            origins.append(frontend_url)
        return origins

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def normalize_log_level(cls, v):
        return v.upper() if isinstance(v, str) else v

    def model_post_init(self, __context):
        """Apply env var aliases after loading."""
        if self.WS_RATE_LIMIT is not None:
            self.WS_MAX_MESSAGES_PER_SECOND = self.WS_RATE_LIMIT
        if self.REST_RATE_LIMIT is not None:
            self.REST_MAX_REQUESTS_PER_MINUTE = self.REST_RATE_LIMIT

    def summary(self) -> dict:
        """Return a non-sensitive summary of current configuration."""
        return {
            "app": self.APP_NAME,
            "version": self.APP_VERSION,
            "environment": self.ENV,
            "host": self.HOST,
            "port": self.PORT,
            "openai_configured": bool(self.OPENAI_API_KEY),
            "openai_model": self.OPENAI_MODEL if self.OPENAI_API_KEY else None,
            "frontend_url": self.FRONTEND_URL,
            "log_level": self.LOG_LEVEL,
        }


# Singleton instance
settings = Settings()

# Apply structured logging
from app.services.logging import setup_logging
setup_logging(env=settings.ENV, level=settings.LOG_LEVEL)

logger = logging.getLogger("signai.config")
logger.info(f"Configuration loaded from: {_env_path}")
logger.info(f"Environment: {settings.ENV} | Version: {settings.APP_VERSION}")
