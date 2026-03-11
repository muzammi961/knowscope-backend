# app/ws/dashboard_ws.py
"""
WebSocket connection manager for real-time dashboard updates.
Endpoint: /ws/dashboard/{user_id}?token=<jwt>
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, List

from fastapi import WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError, ExpiredSignatureError
import os

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET", "")
ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")


# ── Connection Manager ────────────────────────────────────────────────────────

class DashboardConnectionManager:
    """Maintains per-user WebSocket connection pools."""

    def __init__(self):
        # user_id → list of active WebSocket connections
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)
        logger.info("WS connected: user=%s  total_connections=%d",
                    user_id, len(self._connections[user_id]))

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id, [])
        if websocket in sockets:
            sockets.remove(websocket)
        if not sockets:
            self._connections.pop(user_id, None)
        logger.info("WS disconnected: user=%s", user_id)

    async def send_to_user(self, user_id: str, message: dict) -> None:
        """Send a JSON message to all active connections for a user."""
        sockets = list(self._connections.get(user_id, []))
        dead = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    @property
    def active_users(self) -> List[str]:
        return list(self._connections.keys())


# Singleton used across the app
manager = DashboardConnectionManager()


# ── Event helpers ─────────────────────────────────────────────────────────────

def _envelope(event_type: str, data: dict) -> dict:
    return {
        "type":      event_type,
        "data":      data,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def send_dashboard_event(user_id: str, event_type: str, data: dict) -> None:
    """
    Main entry point called by other services to push events.

    Event types:
      - "notification"  → new AI notification
      - "progress"      → subject/topic mastery updated
      - "streak"        → streak updated
      - "ranking"       → ranking changed
      - "heatmap"       → heatmap cell updated
      - "stats"         → full quick-stats refresh
    """
    await manager.send_to_user(user_id, _envelope(event_type, data))


# ── WebSocket endpoint (mounted in main.py) ───────────────────────────────────

async def dashboard_ws_endpoint(websocket: WebSocket, user_id: str, token: str = Query(...)):
    """
    WebSocket connection handler.
    Usage: ws://host/ws/dashboard/{user_id}?token=<jwt>
    """
    # Authenticate via token query param
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_user_id = payload.get("user_id")
        if str(token_user_id) != str(user_id):
            await websocket.close(code=4001, reason="Token user mismatch")
            return
    except ExpiredSignatureError:
        await websocket.close(code=4001, reason="Token expired")
        return
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(user_id, websocket)

    # Send a welcome ping
    await websocket.send_json(_envelope("connected", {
        "message": f"Dashboard live for user {user_id}",
        "active_connections": len(manager._connections.get(user_id, [])),
    }))

    try:
        while True:
            # Keep connection alive; handle ping messages from client
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "ping":
                    await websocket.send_json(_envelope("pong", {}))
            except json.JSONDecodeError:
                pass   # ignore malformed messages
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
