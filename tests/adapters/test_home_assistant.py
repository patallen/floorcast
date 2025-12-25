import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from floorcast.adapters.home_assistant import (
    HAEvent,
    HomeAssistantClient,
    connect_home_assistant,
    map_ha_event,
)


@pytest.fixture
def event_string() -> str:
    return json.dumps(
        {
            "id": 1,
            "type": "event",
            "event": {
                "time_fired": "2020-01-01T00:00:00.000000+00:00",
                "event_type": "state_changed",
                "data": {"entity_id": "light.kitchen"},
                "context": {"id": "fake-id"},
            },
        }
    )


class FakeWebsocket:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.sent: list[str] = []

    async def recv(self) -> str:
        return next(self.responses)

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def __aiter__(self) -> "FakeWebsocket":
        return self

    async def __anext__(self) -> str:
        return await self.recv()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return


@pytest.mark.asyncio
async def test_authenticate_already_authenticated():
    ws = FakeWebsocket(['{"type": "something"}'])
    client = HomeAssistantClient(websocket=ws, auth_token="fake-token")
    await client.authenticate()
    assert not ws.sent


@pytest.mark.asyncio
async def test_authenticate_success():
    ws = FakeWebsocket(
        [
            '{"type": "auth_required"}',
            '{"type": "auth_ok"}',
        ]
    )
    client = HomeAssistantClient(websocket=ws, auth_token="fake-token")
    await client.authenticate()
    assert ws.sent == ['{"type": "auth", "access_token": "fake-token"}']


@pytest.mark.asyncio
async def test_authenticate_failure():
    ws = FakeWebsocket(
        [
            '{"type": "auth_required"}',
            '{"type": "auth_invalid"}',
        ]
    )
    client = HomeAssistantClient(websocket=ws, auth_token="fake-token")
    with pytest.raises(ValueError, match="Failed to authenticate with Home Assistant"):
        await client.authenticate()
    assert ws.sent == ['{"type": "auth", "access_token": "fake-token"}']


@pytest.mark.asyncio
async def test_subscribe():
    ws = FakeWebsocket(['{"id": 1,"type": "result","success": true,"result": null}'])
    client = HomeAssistantClient(websocket=ws, auth_token="fake-token")
    await client.subscribe("state_changed")

    assert ws.sent == ['{"id": 1, "type": "subscribe_events", "event_type": "state_changed"}']


@pytest.mark.asyncio
async def test_anext_ha_event(event_string):
    ws = FakeWebsocket([event_string])
    client = HomeAssistantClient(websocket=ws, auth_token="fake-token")
    event = await client.__anext__()
    assert isinstance(event, HAEvent)
    assert event.entity_id == "light.kitchen"
    assert event.time_fired == datetime(2020, 1, 1, tzinfo=timezone.utc)
    assert event.data == {"entity_id": "light.kitchen"}


@pytest.mark.asyncio
async def test_anext_skips_ha_result(event_string: str):
    ws = FakeWebsocket([json.dumps({"id": 1, "type": "result", "success": True}), event_string])
    client = HomeAssistantClient(websocket=ws, auth_token="fake-token")
    event = await client.__anext__()

    assert isinstance(event, HAEvent)


@pytest.mark.asyncio
async def test_anext_raises_for_invalid_type(event_string: str):
    ws = FakeWebsocket([json.dumps({"id": 1, "type": "bad", "success": True}), event_string])
    client = HomeAssistantClient(websocket=ws, auth_token="fake-token")

    with pytest.raises(ValueError, match="Unexpected message type: 'bad'"):
        await client.__anext__()


@pytest.mark.asyncio
async def test_map_ha_event():
    ha_event = HAEvent(
        id=1,
        event_type="state_changed",
        domain="light",
        entity_id="light.kitchen",
        time_fired=datetime(2020, 1, 1, tzinfo=timezone.utc),
        data={"entity_id": "light.kitchen", "new_state": {"state": "on"}},
        context={"id": "fake-id"},
    )
    mapped_event = await map_ha_event(ha_event)

    assert mapped_event.id == -1
    assert mapped_event.event_type == "state_changed"
    assert mapped_event.domain == "light"
    assert mapped_event.entity_id == "light.kitchen"
    assert mapped_event.timestamp == datetime(2020, 1, 1, tzinfo=timezone.utc)
    assert mapped_event.data == {"state": "on"}


@pytest.mark.asyncio
async def test_connect_home_assistant():
    ws = FakeWebsocket(
        [
            '{"type": "auth_required"}',
            '{"type": "auth_ok"}',
            '{"id": 1,"type": "result","success": true,"result": null}',
        ]
    )
    with patch("floorcast.adapters.home_assistant.connect", return_value=ws) as connect:
        async with connect_home_assistant("http://localhost:8123", "fake-token") as client:
            assert isinstance(client, HomeAssistantClient)
            assert connect.called


@pytest.mark.asyncio
async def test_fetch_registry():
    ws = FakeWebsocket(
        [
            json.dumps(
                {
                    "id": 1,
                    "type": "result",
                    "success": True,
                    "result": [{"floor_id": "floor_1", "name": "First Floor", "level": 1}],
                }
            ),
            json.dumps(
                {
                    "id": 2,
                    "type": "result",
                    "success": True,
                    "result": [
                        {
                            "entity_id": "light.kitchen",
                            "entity_category": None,
                            "device_id": "dev1",
                            "name": "Kitchen Light",
                            "original_name": "Light",
                            "area_id": "kitchen",
                        }
                    ],
                }
            ),
            json.dumps(
                {
                    "id": 3,
                    "type": "result",
                    "success": True,
                    "result": [{"area_id": "kitchen", "name": "Kitchen", "floor_id": "floor_1"}],
                }
            ),
            json.dumps(
                {
                    "id": 4,
                    "type": "result",
                    "success": True,
                    "result": [
                        {
                            "id": "dev1",
                            "name": "Hue Bulb",
                            "name_by_user": None,
                            "area_id": "kitchen",
                        }
                    ],
                }
            ),
        ]
    )
    client = HomeAssistantClient(websocket=ws, auth_token="fake-token")
    registry = await client.fetch_registry()

    assert "light.kitchen" in registry.entities
    assert registry.entities["light.kitchen"].display_name == "Kitchen Light"
    assert "dev1" in registry.devices
    assert "kitchen" in registry.areas
    assert "floor_1" in registry.floors
