from dataclasses import dataclass
from typing import Protocol
from unittest import mock

import pytest

from floorcast.infrastructure.event_bus import TypedEventBus


class MockEvent(Protocol): ...


@dataclass(kw_only=True, frozen=True)
class MockEventSub(MockEvent):
    name: str


@pytest.fixture
def event_bus():
    return TypedEventBus[MockEvent]()


@pytest.mark.asyncio
async def test_typed_bus_subscribe(event_bus: TypedEventBus[MockEvent]):
    mocked_callback = mock.AsyncMock()
    _ = event_bus.subscribe(MockEventSub, mocked_callback)

    event = MockEventSub(name="test")
    event_bus.publish(event)

    await event_bus.wait_all()

    mocked_callback.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_typed_bus_unsubscribe(event_bus: TypedEventBus[MockEvent]):
    mocked_callback = mock.AsyncMock()
    unsubscribe = event_bus.subscribe(MockEventSub, mocked_callback)

    unsubscribe()
    event = MockEventSub(name="test")
    event_bus.publish(event)
    await event_bus.wait_all()
    mocked_callback.assert_not_called()


@pytest.mark.asyncio
async def test_typed_bus_multiple_subscribers(event_bus: TypedEventBus[MockEvent]):
    callback1 = mock.AsyncMock()
    callback2 = mock.AsyncMock()
    event_bus.subscribe(MockEventSub, callback1)
    event_bus.subscribe(MockEventSub, callback2)

    event = MockEventSub(name="test")
    event_bus.publish(event)
    await event_bus.wait_all()

    callback1.assert_called_once_with(event)
    callback2.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_typed_bus_publish_with_no_subscribers(event_bus: TypedEventBus[MockEvent]):
    event = MockEventSub(name="test")
    event_bus.publish(event)  # should not raise
    await event_bus.wait_all()


@pytest.mark.asyncio
async def test_typed_bus_unsubscribe_is_idempotent(event_bus: TypedEventBus[MockEvent]):
    mocked_callback = mock.AsyncMock()
    unsubscribe = event_bus.subscribe(MockEventSub, mocked_callback)

    unsubscribe()
    unsubscribe()  # should not raise

    event = MockEventSub(name="test")
    event_bus.publish(event)
    await event_bus.wait_all()
    mocked_callback.assert_not_called()
