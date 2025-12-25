from fastapi import WebSocket


class SubscriberChannel:
    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket

    async def send_connected(self, subscriber_id: str) -> None:
        await self._ws.send_json({"type": "connected", "subscriber_id": subscriber_id})

    async def send_snapshot(self, state: dict[str, str | None]) -> None:
        await self._ws.send_json({"type": "snapshot", "state": state})

    async def send_event(self, entity_id: str, state: str | None) -> None:
        await self._ws.send_json({"type": "event", "entity_id": entity_id, "state": state})
