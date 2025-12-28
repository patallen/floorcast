import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from typing import Any, AsyncIterator, cast

import structlog
from websockets import connect
from websockets.asyncio.client import ClientConnection

from floorcast.domain.models import Area, Device, Entity, Event, Floor, Registry

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

    async def fetch_registry(self) -> Registry:
        floor_data = await self._call_wait("config/floor_registry/list")
        entity_data = await self._call_wait("config/entity_registry/list")
        area_data = await self._call_wait("config/area_registry/list")
        device_data = await self._call_wait("config/device_registry/list")
        registry = Registry(
            entities={e.id: e for e in (Entity.from_dict(e) for e in entity_data)},
            floors={f.id: f for f in (Floor.from_dict(f) for f in floor_data)},
            areas={a.id: a for a in (Area.from_dict(a) for a in area_data)},
            devices={d.id: d for d in (Device.from_dict(d) for d in device_data)},
        )
        logger.info(
            "fetched registry from home assistant",
            entities=len(registry.entities),
            floors=len(registry.floors),
            areas=len(registry.areas),
            devices=len(registry.devices),
        )
        return registry

    async def send_json(self, data: dict[str, Any]) -> None:
        await self._websocket.send(json.dumps(data))

    async def recv_json(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(await self._websocket.recv()))

    async def authenticate(self) -> None:
        res = json.loads(await self._websocket.recv())
        if not res["type"] == "auth_required":
            logger.info("Home Assistant authentication not required")
            return

        await self.send_json({"type": "auth", "access_token": self._auth_token})

        result = await self.recv_json()

        if not result["type"] == "auth_ok":
            raise ValueError("Failed to authenticate with Home Assistant")
        logger.info("authenticated with home assistant")

    async def subscribe(self, event_type: str) -> int:
        next_id = next(self._counter)
        await self.send_json({"id": next_id, "type": "subscribe_events", "event_type": event_type})
        # TODO: Do something if this fails
        #  '{"id": 1,"type": "result","success": false,"result": null}'
        await self.recv_json()
        logger.info("subscribed to home assistant events", event_type=event_type)
        return next_id

    async def _receive(self) -> HAEvent | HAResult:
        data = await self.recv_json()
        message_type = data["type"]
        if message_type == "result":
            return _create_ha_result(data)
        if message_type == "event":
            return _create_ha_event(data)

        raise ValueError(f"Unexpected message type: '{data['type']}'")

    async def _call_wait(self, method: str) -> list[dict[str, Any]]:
        command_id = next(self._counter)
        await self.send_json({"id": command_id, "type": method})
        res = await self.recv_json()
        assert res["id"] == command_id, "Unexpected response id"
        return cast(list[dict[str, Any]], res["result"])

    def __aiter__(self) -> "HomeAssistantClient":  # pragma: no cover
        return self

    async def __anext__(self) -> Event:
        while True:
            message = await self._receive()
            if not isinstance(message, HAEvent):
                logger.warning(
                    f"HAResult received while iterating {self.__class__.__name__}",
                    result=message,
                )
                continue
            return _map_to_domain_event(message)

    async def __aenter__(self) -> "HomeAssistantClient":
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
        time_fired=datetime.fromisoformat(event["time_fired"]).replace(tzinfo=timezone.utc),
        data=event["data"],
        context=event["context"],
    )


def _create_ha_result(data: dict[str, Any]) -> HAResult:
    return HAResult(id=data["id"], success=data["success"], result=data.get("result"))


def _map_to_domain_event(ha_event: HAEvent) -> Event:
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
        unit=new_state.get("attributes", {}).get("unit_of_measurement"),
    )


@asynccontextmanager
async def connect_home_assistant(url: str, token: str) -> AsyncIterator[HomeAssistantClient]:
    async with connect(url) as ws:
        async with HomeAssistantClient(ws, token) as client:
            logger.info("connected to home assistant", url=url)
            await client.subscribe("state_changed")
            yield client
