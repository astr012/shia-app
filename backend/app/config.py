# ============================================================
# SignAI_OS â€” Centralized Configuration
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

    # â”€â”€ Server â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # â”€â”€ Version â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    APP_VERSION: str = "2.3.0"
    APP_NAME: str = "SignAI_OS"

    # â”€â”€ CORS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    ALLOWED_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS: list[str] = [
        "Authorization", "Content-Type", "X-Request-ID",
        "Accept", "Origin", "X-Requested-With",
    ]

    # â”€â”€ CSRF â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    CSRF_TRUSTED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # â”€â”€ Content Security Policy â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    CSP_DIRECTIVES: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' ws://localhost:* wss://localhost:* http://localhost:* "
        "https://*.onrender.com wss://*.onrender.com https://*.vercel.app; "
        "media-src 'self' blob:; "
        "worker-src 'self' blob:;"
    )

    # â”€â”€ Password Policy â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True

    # â”€â”€ OpenAI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # â”€â”€ Auth â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    JWT_SECRET_KEY: str = "super-secret-default-key-please-change"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # â”€â”€ Redis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    REDIS_URL: Optional[str] = None

    # â”€â”€ Rate Limiting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    WS_MAX_MESSAGES_PER_SECOND: int = 20
    REST_MAX_REQUESTS_PER_MINUTE: int = 60

    # â”€â”€ Aliases for env var names â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    WS_RATE_LIMIT: Optional[int] = None      # Maps to WS_MAX_MESSAGES_PER_SECOND
    REST_RATE_LIMIT: Optional[int] = None     # Maps to REST_MAX_REQUESTS_PER_MINUTE

    # â”€â”€ Analytics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ANALYTICS_MAX_LATENCY_SAMPLES: int = 500

    # â”€â”€ Logging â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
            origins = [o.strip().rstrip("/") for o in v.split(",")]
        else:
            origins = [o.rstrip("/") for o in v] if v else []
        frontend_url = info.data.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
        if frontend_url not in origins:
            origins.append(frontend_url)
        return origins

    @field_validator("CSRF_TRUSTED_ORIGINS", mode="before")
    @classmethod
    def assemble_csrf_origins(cls, v, info):
        """Ensure FRONTEND_URL is always in the CSRF trusted origins."""
        if isinstance(v, str):
            origins = [o.strip().rstrip("/") for o in v.split(",")]
        else:
            origins = [o.rstrip("/") for o in v] if v else []
        frontend_url = info.data.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
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
