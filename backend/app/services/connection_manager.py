# ============================================================
# SignAI_OS — WebSocket Connection Manager
# Manages multiple concurrent WebSocket connections
# ============================================================

from fastapi import WebSocket, status
from typing import Dict
import logging
import time
import asyncio

logger = logging.getLogger("signai.connections")

MAX_CONNECTIONS = 500  # Threshold to trigger circuit breaker

class ConnectionManager:
    """
    Manages active WebSocket connections.
    Includes circuit breaker logic to shed idle connections and restrict new handshakes.
    """

    def __init__(self):
        # Maps WebSocket to last activity timestamp
        self._active_connections: Dict[WebSocket, float] = {}

    async def connect(self, websocket: WebSocket) -> bool:
        """Accept and register a new WebSocket connection. Returns True if accepted, False if rejected."""
        # Circuit Breaker: Restrict new handshakes if memory/connection bounds reached
        if len(self._active_connections) >= MAX_CONNECTIONS:
            logger.warning("[Circuit Breaker] Connection limit reached. Shedding idle and rejecting new handshake.")
            await self.shed_idle_connections(idle_timeout=60.0) # aggressively shed idle
            if len(self._active_connections) >= MAX_CONNECTIONS:
                # If still full after shedding, reject
                await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER, reason="Server overloaded")
                return False

        await websocket.accept()
        self._active_connections[websocket] = time.time()
        logger.info(f"New connection. Total active: {len(self._active_connections)}")
        return True

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self._active_connections:
            self._active_connections.pop(websocket, None)
            logger.info(f"Connection removed. Total active: {len(self._active_connections)}")

    def record_activity(self, websocket: WebSocket):
        """Update last active timestamp for a connection."""
        if websocket in self._active_connections:
            self._active_connections[websocket] = time.time()

    async def shed_idle_connections(self, idle_timeout: float = 300.0):
        """Circuit breaker logic to shed idle connections."""
        now = time.time()
        to_remove = [ws for ws, last_active in self._active_connections.items() if now - last_active > idle_timeout]
        
        for ws in to_remove:
            logger.info("[Circuit Breaker] Shedding idle connection.")
            try:
                await ws.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Idle timeout")
            except Exception:
                pass
            self.disconnect(ws)

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        disconnected = []
        for connection in list(self._active_connections.keys()):
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up dead connections
        for conn in disconnected:
            self.disconnect(conn)

    async def send_to(self, websocket: WebSocket, message: dict):
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.disconnect(websocket)

    def active_count(self) -> int:
        """Return the number of active connections."""
        return len(self._active_connections)
