# ============================================================
# SignAI_OS — WebSocket Connection Manager
# Manages multiple concurrent WebSocket connections
# ============================================================

from fastapi import WebSocket
from typing import List
import logging

logger = logging.getLogger("signai.connections")


class ConnectionManager:
    """
    Manages active WebSocket connections.
    Supports broadcasting to all clients and targeted messaging.
    """

    def __init__(self):
        self._active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self._active_connections.append(websocket)
        logger.info(f"New connection. Total active: {len(self._active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)
            logger.info(f"Connection removed. Total active: {len(self._active_connections)}")

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        disconnected = []
        for connection in self._active_connections:
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
