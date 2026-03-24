# ============================================================
# SignAI_OS — Centralized Configuration
#
# Loads settings from .env and provides typed config access
# across the entire backend application.
# ============================================================

import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from the backend root directory
_backend_root = Path(__file__).resolve().parent.parent
_env_path = _backend_root / ".env"
load_dotenv(dotenv_path=_env_path)

logger = logging.getLogger("signai.config")


class Settings:
    """
    Application-wide settings.
    Reads from environment variables with sensible defaults.
    """

    # ── Server ───────────────────────────────────────────────
    ENV: str = os.getenv("ENV", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = ENV == "development"

    # ── Version ──────────────────────────────────────────────
    APP_VERSION: str = "2.2.0-beta"
    APP_NAME: str = "SignAI_OS"

    # ── CORS ─────────────────────────────────────────────────
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        FRONTEND_URL,
    ]

    # ── OpenAI ───────────────────────────────────────────────
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY") or None
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # ── Rate Limiting ────────────────────────────────────────
    WS_MAX_MESSAGES_PER_SECOND: int = int(os.getenv("WS_RATE_LIMIT", "20"))
    REST_MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("REST_RATE_LIMIT", "60"))

    # ── Analytics ────────────────────────────────────────────
    ANALYTICS_MAX_LATENCY_SAMPLES: int = 500

    # ── Logging ──────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    @classmethod
    def summary(cls) -> dict:
        """Return a non-sensitive summary of current configuration."""
        return {
            "app": cls.APP_NAME,
            "version": cls.APP_VERSION,
            "environment": cls.ENV,
            "host": cls.HOST,
            "port": cls.PORT,
            "openai_configured": bool(cls.OPENAI_API_KEY),
            "openai_model": cls.OPENAI_MODEL if cls.OPENAI_API_KEY else None,
            "frontend_url": cls.FRONTEND_URL,
            "log_level": cls.LOG_LEVEL,
        }


# Singleton instance
settings = Settings()

# Apply log level
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)

logger.info(f"Configuration loaded from: {_env_path}")
logger.info(f"Environment: {settings.ENV} | Version: {settings.APP_VERSION}")
