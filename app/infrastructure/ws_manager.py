import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WebSocket connected. Total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WebSocket disconnected. Total: %d", len(self._connections))

    async def broadcast(self, data: dict) -> None:
        for ws in list(self._connections):
            try:
                await ws.send_json(data)
            except Exception:
                self._connections.discard(ws)


ws_manager = ConnectionManager()
