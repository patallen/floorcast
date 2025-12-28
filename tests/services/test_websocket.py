import uuid
from datetime import datetime, timezone
from unittest import mock

import pytest

from floorcast.domain.events import EntityStateChanged, FCEvent
from floorcast.domain.models import Event
from floorcast.domain.websocket import WSConnection, WSMessage
from floorcast.infrastructure.event_bus import TypedEventBus
from floorcast.services.registry import RegistryService
from floorcast.services.state import StateService
from floorcast.services.websocket import WebsocketService


@pytest.fixture
def event_bus():
    return mock.AsyncMock(spec=TypedEventBus[FCEvent])


@pytest.fixture
def state_service():
    return mock.Mock(spec=StateService)


@pytest.fixture
def registry_service():
    return mock.Mock(spec=RegistryService)


@pytest.mark.asyncio
async def test_websocket_connect(event_bus, state_service, registry_service):
    service = WebsocketService(
        bus=event_bus, state_service=state_service, registry_service=registry_service
    )

    conn = service.connect()

    assert isinstance(conn, WSConnection)
    assert conn.queue.empty()
    assert len(service._clients) == 1


@pytest.mark.asyncio
async def test_websocket_disconnect(event_bus, state_service, registry_service):
    service = WebsocketService(
        bus=event_bus, state_service=state_service, registry_service=registry_service
    )

    conn = service.connect()
    assert len(service._clients) == 1

    service.disconnect(conn)
    assert len(service._clients) == 0


@pytest.mark.asyncio
async def test_websocket_send_message(event_bus, state_service, registry_service):
    service = WebsocketService(
        bus=event_bus, state_service=state_service, registry_service=registry_service
    )
    conn = service.connect()

    service.send_message(conn, WSMessage("subscribe", "entity_states"))

    assert "entity_states" in service._subscriptions
    assert conn in service._subscriptions["entity_states"]

    service.send_message(conn, WSMessage("unsubscribe", "entity_states"))
    assert conn not in service._subscriptions["entity_states"]

    service.send_message(conn, WSMessage("ping", None))
    assert conn.queue.get_nowait() == WSMessage("pong", None)

    with pytest.raises(ValueError):
        service.send_message(conn, WSMessage("unknown", None))


@pytest.mark.asyncio
async def test_request_registry(event_bus, state_service, registry_service):
    service = WebsocketService(
        bus=event_bus, state_service=state_service, registry_service=registry_service
    )
    conn = service.connect()

    await service.request_registry(conn)
    registry_service.get_registry.assert_called_once()
    assert conn.queue.get_nowait().type == "registry"


@pytest.mark.asyncio
async def test_request_snapshot(event_bus, state_service, registry_service):
    service = WebsocketService(
        bus=event_bus, state_service=state_service, registry_service=registry_service
    )
    conn = service.connect()

    await service.request_snapshot(conn)
    state_service.get_state_at.assert_called_once()
    assert conn.queue.get_nowait().type == "snapshot"


@pytest.mark.asyncio
async def test_init_subscribes_to_events():
    bus = TypedEventBus()
    service = WebsocketService(bus=bus, state_service=mock.Mock(), registry_service=mock.Mock())

    conn = service.connect()
    service.send_message(conn, WSMessage("subscribe", "entity_states"))
    mock_event = Event(
        id=1,
        event_type="entity.state_change",
        entity_id="fake",
        event_id=uuid.uuid4(),
        state="fake",
        timestamp=datetime.now(tz=timezone.utc),
        data={},
        domain="light",
        external_id="lol",
    )
    bus.publish(
        EntityStateChanged(
            entity_id="fake",
            state="fake",
            event=mock_event,
        )
    )

    message = await conn.queue.get()
    assert isinstance(message, WSMessage)
    assert message.type == "entity.state_change"


def test_subscribing_to_unknown_topic_raises_error():
    bus = TypedEventBus()
    service = WebsocketService(bus=bus, state_service=mock.Mock(), registry_service=mock.Mock())
    conn = service.connect()
    with pytest.raises(ValueError):
        service.send_message(conn, WSMessage("subscribe", "unknown"))

    with pytest.raises(ValueError):
        service.send_message(conn, WSMessage("unsubscribe", "unknown"))
