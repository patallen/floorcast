import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from typing import Any, AsyncIterator

import structlog
from websockets import connect
from websockets.asyncio.client import ClientConnection

from floorcast.domain.models import Event

logger = structlog.get_logger(__name__)


@dataclass(kw_only=True, frozen=True)
class HAEvent:
    id: int
    event_type: str
    domain: str
    entity_id: str
    time_fired: datetime
    data: dict[str, Any]
    context: dict[str, Any]


@dataclass(kw_only=True, frozen=True)
class HAResult:
    id: int
    success: bool
    result: dict[str, Any] | None = None


class HomeAssistantClient:
    def __init__(self, websocket: ClientConnection, auth_token: str):
        self._websocket = websocket
        self._auth_token = auth_token
        self._counter = count(1)

    async def authenticate(self) -> None:
        res = json.loads(await self._websocket.recv())
        if not res["type"] == "auth_required":
            logger.info("Home Assistant authentication not required")
            return

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
        # TODO: Do something if this fails
        #  '{"id": 1,"type": "result","success": false,"result": null}'
        await self._websocket.recv()
        return next_id

    async def _receive(self) -> HAEvent | HAResult:
        result = await self._websocket.recv()
        data = json.loads(result)
        message_type = data["type"]
        if message_type == "result":
            return _create_ha_result(data)
        if message_type == "event":
            return _create_ha_event(data)

        raise ValueError(f"Unexpected message type: '{data['type']}'")

    def __aiter__(self) -> "HomeAssistantClient":  # pragma: no cover
        return self

    async def __anext__(self) -> HAEvent:
        while True:
            message = await self._receive()
            if not isinstance(message, HAEvent):
                logger.warning(
                    f"HAResult received while iterating {self.__class__.__name__}",
                    result=message,
                )
                continue
            return message

    async def __aenter__(self) -> "HomeAssistantClient":
        _ = await self._websocket.recv()
        await self.authenticate()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException], exc_value: BaseException, traceback: Any
    ) -> bool | None: ...


def _create_ha_event(data: dict[str, Any]) -> HAEvent:
    event = data["event"]
    entity_id = event["data"]["entity_id"]
    return HAEvent(
        id=data["id"],
        event_type=event["event_type"],
        domain=entity_id.split(".")[0],
        entity_id=entity_id,
        time_fired=datetime.fromisoformat(event["time_fired"]).replace(
            tzinfo=timezone.utc
        ),
        data=event["data"],
        context=event["context"],
    )


def _create_ha_result(data: dict[str, Any]) -> HAResult:
    return HAResult(id=data["id"], success=data["success"], result=data.get("result"))


async def map_ha_event(ha_event: HAEvent) -> Event:
    data = ha_event.data
    new_state = data.get("new_state") or {}
    state = new_state.get("state")
    external_id = ha_event.context["id"]

    return Event(
        external_id=external_id,
        entity_id=ha_event.entity_id,
        domain=ha_event.domain,
        event_id=uuid.uuid4(),
        state=state,
        event_type=ha_event.event_type,
        timestamp=ha_event.time_fired,
        data=new_state,
    )


@asynccontextmanager
async def connect_home_assistant(
    url: str, token: str
) -> AsyncIterator[HomeAssistantClient]:
    async with connect(url) as ws:
        async with HomeAssistantClient(ws, token) as client:
            await client.subscribe("state_changed")
            logger.info("connected to home assistant", url=url)
            yield client
