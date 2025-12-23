import json
from dataclasses import dataclass
from datetime import datetime
from itertools import count
from typing import Any

from structlog import get_logger
from websockets.asyncio.client import ClientConnection

logger = get_logger(__name__)


@dataclass(kw_only=True, frozen=True)
class HAEvent:
    id: int
    event_type: str
    time_fired: datetime
    data: dict[str, Any]
    context: dict[str, Any]


@dataclass(kw_only=True, frozen=True)
class HAResult:
    id: int
    success: bool
    result: dict | None = None


class HomeAssistantProtocol:
    def __init__(self, websocket: ClientConnection, auth_token: str):
        self._websocket = websocket
        self._auth_token = auth_token
        self._counter = count(1)

    async def authenticate(self) -> None:
        auth_payload = json.dumps({"type": "auth", "access_token": self._auth_token})
        await self._websocket.send(auth_payload)

        result = await self._websocket.recv()
        if not json.loads(result)["type"] == "auth_ok":
            raise ValueError("Failed to authenticate with Home Assistant")

    async def subscribe(self, event_type: str) -> int:
        next_id = next(self._counter)
        await self._websocket.send(
            json.dumps(
                {"id": next_id, "type": "subscribe_events", "event_type": event_type}
            )
        )
        await self._websocket.recv()
        return next_id

    async def _receive(self) -> HAEvent | HAResult:
        result = await self._websocket.recv()
        data = json.loads(result)
        if data["type"] == "result":
            return HAResult(
                id=data["id"], success=data["success"], result=data.get("result")
            )
        if data["type"] == "event":
            event = data["event"]
            return HAEvent(
                id=data["id"],
                event_type=event["event_type"],
                time_fired=datetime.fromisoformat(event["time_fired"]),
                data=event["data"],
                context=event["context"],
            )

        raise ValueError(f"Unknown message type: {data['type']}")

    def __aiter__(self):
        return self

    async def __anext__(self):
        while True:
            message = await self._receive()
            if isinstance(message, HAResult):
                logger.warning(
                    "HAResult received while iterating HomeAssistantProtocol",
                    result=message,
                )
                continue
            if isinstance(message, HAEvent):
                return message

    async def __aenter__(self) -> "HomeAssistantProtocol":
        _ = await self._websocket.recv()
        await self.authenticate()
        return self

    async def __aexit__(self, _exc_type, _exc, _tb) -> None: ...
