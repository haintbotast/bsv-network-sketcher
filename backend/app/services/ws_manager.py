"""Quản lý WebSocket connections theo project."""

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, project_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(project_id, set()).add(websocket)

    def disconnect(self, project_id: str, websocket: WebSocket) -> None:
        if project_id not in self._connections:
            return
        self._connections[project_id].discard(websocket)
        if not self._connections[project_id]:
            self._connections.pop(project_id, None)

    async def send_json(self, websocket: WebSocket, message: dict) -> None:
        await websocket.send_json(message)

    async def broadcast(self, project_id: str, message: dict) -> None:
        connections = list(self._connections.get(project_id, set()))
        for websocket in connections:
            await websocket.send_json(message)


ws_manager = ConnectionManager()
