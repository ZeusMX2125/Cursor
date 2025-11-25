"""WebSocket manager for frontend connections and real-time data broadcasting."""

import asyncio
import json
from typing import Dict, List, Set
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger


class WebSocketManager:
    """Manages WebSocket connections to frontend clients and broadcasts real-time data."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict) -> None:
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        disconnected = set()

        async with self._lock:
            connections = list(self.active_connections)

        for connection in connections:
            try:
                await connection.send_text(message_json)
            except (RuntimeError, ConnectionError, OSError) as e:
                # Connection is closed or broken - remove it silently
                logger.debug(f"WebSocket client disconnected during broadcast: {type(e).__name__}")
                disconnected.add(connection)
            except Exception as e:
                # Other errors - log but still remove connection
                logger.debug(f"WebSocket error during broadcast: {type(e).__name__}: {e}")
                disconnected.add(connection)

        # Remove disconnected clients
        if disconnected:
            async with self._lock:
                self.active_connections -= disconnected
                if disconnected:
                    logger.debug(f"Removed {len(disconnected)} disconnected WebSocket clients")

    async def send_personal_message(self, message: Dict, websocket: WebSocket) -> None:
        """Send a message to a specific client."""
        try:
            message_json = json.dumps(message)
            await websocket.send_text(message_json)
        except Exception as e:
            logger.warning(f"Error sending personal message: {e}")

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()

