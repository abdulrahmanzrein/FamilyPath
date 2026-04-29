# tracks all open websocket connections, grouped by search_id
# any agent (or fake_runner) can call hub.broadcast(search_id, event) and
# every dashboard subscribed to that search gets the event in real time

from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class WebSocketHub:
    def __init__(self) -> None:
        # one set of sockets per search_id (a search can have multiple viewers)
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, search_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()  # finishes the WS handshake
        self._connections[search_id].add(websocket)

    def disconnect(self, search_id: UUID, websocket: WebSocket) -> None:
        self._connections[search_id].discard(websocket)
        # tidy up empty entries so the dict doesn't grow forever
        if not self._connections[search_id]:
            self._connections.pop(search_id, None)

    async def broadcast(self, search_id: UUID, event: dict) -> None:
        # snapshot the set so we can mutate during iteration if a send fails
        for ws in list(self._connections.get(search_id, set())):
            try:
                await ws.send_json(event)
            except Exception:
                # client disconnected mid-broadcast — drop it and keep going
                self.disconnect(search_id, ws)


# single shared instance imported by routes + the fake runner
hub = WebSocketHub()
