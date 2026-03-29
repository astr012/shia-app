# ============================================================
# SignAI_OS — Structured JSON Logging
#
# Production-grade logging: JSON in production, human-readable
# in development. Includes correlation ID propagation.
# ============================================================

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

# Context variable for request correlation
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "correlation_id": correlation_id.get("-"),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


class DevFormatter(logging.Formatter):
    """Human-readable colored formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        cid = correlation_id.get("-")
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = f"{ts} | {color}{record.levelname:7s}{self.RESET} | {record.name:20s}"
        msg = record.getMessage()
        if cid != "-":
            return f"{prefix} | [{cid}] {msg}"
        return f"{prefix} | {msg}"


def setup_logging(env: str = "development", level: str = "INFO"):
    """Configure logging based on environment."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if env == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(DevFormatter())

    root.addHandler(handler)

    # Quiet down noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
