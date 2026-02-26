from fastapi import WebSocket
from typing import Dict, List
import json


class ConnectionManager:
    """
    Manages WebSocket connections per clinic.
    When a new appointment is booked, we broadcast only to
    admins of that specific clinic (multi-tenant isolation).
    """

    def __init__(self):
        # clinic_id → list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, clinic_id: str):
        await websocket.accept()
        if clinic_id not in self.active_connections:
            self.active_connections[clinic_id] = []
        self.active_connections[clinic_id].append(websocket)
        print(f"🔌 WS connected: clinic={clinic_id}, total={len(self.active_connections[clinic_id])}")

    def disconnect(self, websocket: WebSocket, clinic_id: str):
        if clinic_id in self.active_connections:
            self.active_connections[clinic_id].remove(websocket)
            if not self.active_connections[clinic_id]:
                del self.active_connections[clinic_id]
        print(f"🔌 WS disconnected: clinic={clinic_id}")

    async def broadcast_to_clinic(self, clinic_id: str, event_type: str, data: dict):
        """Send a JSON event to all admin dashboards watching this clinic."""
        if clinic_id not in self.active_connections:
            return

        message = json.dumps({"event": event_type, "data": data})
        dead_connections = []

        for websocket in self.active_connections[clinic_id]:
            try:
                await websocket.send_text(message)
            except Exception:
                dead_connections.append(websocket)

        # Clean up dead connections
        for ws in dead_connections:
            self.active_connections[clinic_id].remove(ws)

    async def send_personal_message(self, websocket: WebSocket, event_type: str, data: dict):
        message = json.dumps({"event": event_type, "data": data})
        await websocket.send_text(message)


# Singleton instance — shared across the entire app
ws_manager = ConnectionManager()
