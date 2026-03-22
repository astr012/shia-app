# ============================================================
# Shia — Analytics & Metrics Service
#
# Tracks system-wide usage metrics: translations processed,
# average latency, active sessions, and uptime.
# All data is in-memory (resets on server restart).
# ============================================================

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("shia.analytics")


@dataclass
class SessionStats:
    """Stats for a single WebSocket session."""
    session_id: str
    connected_at: float = field(default_factory=time.time)
    gestures_processed: int = 0
    speeches_processed: int = 0
    total_requests: int = 0
    errors: int = 0

    @property
    def duration_seconds(self) -> float:
        return time.time() - self.connected_at


@dataclass
class LatencySample:
    """A single latency measurement."""
    operation: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


class AnalyticsService:
    """
    Lightweight in-memory analytics for tracking system health and usage.
    """

    def __init__(self):
        self._boot_time = time.time()
        self._sessions: Dict[str, SessionStats] = {}
        self._latency_samples: List[LatencySample] = []
        self._total_translations: int = 0
        self._total_sign_conversions: int = 0
        self._total_errors: int = 0
        self._max_latency_samples: int = 500  # Rolling window

    # ── Session Tracking ─────────────────────────────────────

    def register_session(self, session_id: str) -> SessionStats:
        """Register a new WebSocket session."""
        stats = SessionStats(session_id=session_id)
        self._sessions[session_id] = stats
        logger.info(f"Session registered: {session_id}")
        return stats

    def unregister_session(self, session_id: str) -> Optional[SessionStats]:
        """Remove a session and return its final stats."""
        stats = self._sessions.pop(session_id, None)
        if stats:
            logger.info(
                f"Session ended: {session_id} | "
                f"Duration: {stats.duration_seconds:.1f}s | "
                f"Requests: {stats.total_requests} | "
                f"Errors: {stats.errors}"
            )
        return stats

    def record_request(self, session_id: str, request_type: str):
        """Record a request for a session."""
        if session_id in self._sessions:
            self._sessions[session_id].total_requests += 1
            if request_type == "gesture_sequence":
                self._sessions[session_id].gestures_processed += 1
                self._total_translations += 1
            elif request_type == "speech_input":
                self._sessions[session_id].speeches_processed += 1
                self._total_sign_conversions += 1

    def record_error(self, session_id: str):
        """Record an error for a session."""
        self._total_errors += 1
        if session_id in self._sessions:
            self._sessions[session_id].errors += 1

    # ── Latency Tracking ─────────────────────────────────────

    def record_latency(self, operation: str, duration_ms: float):
        """Record a latency sample."""
        self._latency_samples.append(LatencySample(
            operation=operation,
            duration_ms=duration_ms,
        ))
        # Trim to rolling window
        if len(self._latency_samples) > self._max_latency_samples:
            self._latency_samples = self._latency_samples[-self._max_latency_samples:]

    # ── Reporting ─────────────────────────────────────────────

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._boot_time

    @property
    def uptime_formatted(self) -> str:
        seconds = int(self.uptime_seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours}h {minutes}m {secs}s"

    def get_avg_latency(self, operation: Optional[str] = None) -> float:
        """Get average latency in ms, optionally filtered by operation."""
        samples = self._latency_samples
        if operation:
            samples = [s for s in samples if s.operation == operation]
        if not samples:
            return 0.0
        return sum(s.duration_ms for s in samples) / len(samples)

    def get_summary(self) -> dict:
        """Get a complete analytics summary."""
        return {
            "uptime": self.uptime_formatted,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "active_sessions": len(self._sessions),
            "total_translations": self._total_translations,
            "total_sign_conversions": self._total_sign_conversions,
            "total_errors": self._total_errors,
            "avg_latency_ms": round(self.get_avg_latency(), 1),
            "avg_grammar_latency_ms": round(self.get_avg_latency("grammar"), 1),
            "avg_translation_latency_ms": round(self.get_avg_latency("translation"), 1),
            "boot_time": datetime.fromtimestamp(self._boot_time).isoformat(),
        }
