# ============================================================
# SignAI_OS — Session Manager
#
# Assigns unique session IDs to each WebSocket connection and
# tracks per-session metadata (mode, requests, duration, etc.)
# Works alongside the ConnectionManager and AnalyticsService.
# ============================================================

import uuid
import time
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field

from fastapi import WebSocket

logger = logging.getLogger("signai.sessions")


@dataclass
class Session:
    """Represents a single WebSocket client session."""
    session_id: str
    websocket: WebSocket
    connected_at: float = field(default_factory=time.time)
    mode: str = "SIGN_TO_SPEECH"
    gestures_sent: int = 0
    speeches_sent: int = 0
    manual_inputs: int = 0
    errors: int = 0
    last_active: float = field(default_factory=time.time)

    @property
    def duration_seconds(self) -> float:
        return time.time() - self.connected_at

    @property
    def total_requests(self) -> int:
        return self.gestures_sent + self.speeches_sent + self.manual_inputs

    def touch(self):
        """Update last active timestamp."""
        self.last_active = time.time()

    def to_dict(self) -> dict:
        """Serialize session info (excluding websocket)."""
        return {
            "session_id": self.session_id,
            "connected_at": self.connected_at,
            "duration_seconds": round(self.duration_seconds, 1),
            "mode": self.mode,
            "gestures_sent": self.gestures_sent,
            "speeches_sent": self.speeches_sent,
            "manual_inputs": self.manual_inputs,
            "total_requests": self.total_requests,
            "errors": self.errors,
            "last_active": self.last_active,
        }


class SessionManager:
    """
    Manages WebSocket sessions with unique IDs.
    Provides session lookup, statistics, and lifecycle management.
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._ws_to_session: Dict[int, str] = {}  # ws id → session_id
        self._total_sessions_served: int = 0

    def create_session(self, websocket: WebSocket) -> Session:
        """Create and register a new session for a WebSocket connection."""
        session_id = str(uuid.uuid4())[:8]  # Short ID for readability
        session = Session(session_id=session_id, websocket=websocket)

        self._sessions[session_id] = session
        self._ws_to_session[id(websocket)] = session_id
        self._total_sessions_served += 1

        logger.info(
            f"Session created: {session_id} | "
            f"Active sessions: {len(self._sessions)}"
        )
        return session

    def remove_session(self, websocket: WebSocket) -> Optional[Session]:
        """Remove a session by its WebSocket reference."""
        session_id = self._ws_to_session.pop(id(websocket), None)
        if session_id:
            session = self._sessions.pop(session_id, None)
            if session:
                logger.info(
                    f"Session ended: {session_id} | "
                    f"Duration: {session.duration_seconds:.1f}s | "
                    f"Requests: {session.total_requests} | "
                    f"Errors: {session.errors}"
                )
                return session
        return None

    def get_session(self, websocket: WebSocket) -> Optional[Session]:
        """Get session by WebSocket reference."""
        session_id = self._ws_to_session.get(id(websocket))
        if session_id:
            return self._sessions.get(session_id)
        return None

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Get session by its ID."""
        return self._sessions.get(session_id)

    def record_gesture(self, websocket: WebSocket):
        """Record a gesture request for a session."""
        session = self.get_session(websocket)
        if session:
            session.gestures_sent += 1
            session.touch()

    def record_speech(self, websocket: WebSocket):
        """Record a speech request for a session."""
        session = self.get_session(websocket)
        if session:
            session.speeches_sent += 1
            session.touch()

    def record_manual(self, websocket: WebSocket):
        """Record a manual input for a session."""
        session = self.get_session(websocket)
        if session:
            session.manual_inputs += 1
            session.touch()

    def record_error(self, websocket: WebSocket):
        """Record an error for a session."""
        session = self.get_session(websocket)
        if session:
            session.errors += 1

    def set_mode(self, websocket: WebSocket, mode: str):
        """Update session mode."""
        session = self.get_session(websocket)
        if session:
            session.mode = mode

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    @property
    def total_served(self) -> int:
        return self._total_sessions_served

    def get_all_sessions(self) -> List[dict]:
        """Return all active sessions as serializable dicts."""
        return [s.to_dict() for s in self._sessions.values()]

    def get_summary(self) -> dict:
        """Return a summary of session activity."""
        return {
            "active_sessions": self.active_count,
            "total_sessions_served": self._total_sessions_served,
            "sessions": self.get_all_sessions(),
        }
