import asyncio
from dataclasses import dataclass
from typing import Protocol
from unittest import mock

import pytest

from floorcast.infrastructure.event_bus import EventBus, TypedEventBus


def test_subscribe_adds_queue():
    bus: EventBus[str] = EventBus()
    queue: asyncio.Queue[str] = asyncio.Queue()

    bus.subscribe(queue)

    assert queue in bus._subscribers


def test_unsubscribe_removes_queue():
    bus: EventBus[str] = EventBus()
    queue: asyncio.Queue[str] = asyncio.Queue()

    unsubscribe = bus.subscribe(queue)
    assert queue in bus._subscribers

    unsubscribe()
    assert queue not in bus._subscribers


def test_unsubscribe_is_idempotent():
    bus: EventBus[str] = EventBus()
    queue: asyncio.Queue[str] = asyncio.Queue()

    unsubscribe = bus.subscribe(queue)
    unsubscribe()
    unsubscribe()  # should not raise

    assert queue not in bus._subscribers


def test_publish_sends_to_subscriber():
    bus: EventBus[str] = EventBus()
    queue: asyncio.Queue[str] = asyncio.Queue()
    bus.subscribe(queue)

    bus.publish("test_event")

    assert queue.get_nowait() == "test_event"


def test_publish_sends_to_multiple_subscribers():
    bus: EventBus[str] = EventBus()
    queue1: asyncio.Queue[str] = asyncio.Queue()
    queue2: asyncio.Queue[str] = asyncio.Queue()
    bus.subscribe(queue1)
    bus.subscribe(queue2)

    bus.publish("test_event")

    assert queue1.get_nowait() == "test_event"
    assert queue2.get_nowait() == "test_event"


def test_publish_with_no_subscribers():
    bus: EventBus[str] = EventBus()

    bus.publish("test_event")  # should not raise


def test_publish_does_not_send_to_unsubscribed():
    bus: EventBus[str] = EventBus()
    queue: asyncio.Queue[str] = asyncio.Queue()
    unsubscribe = bus.subscribe(queue)

    unsubscribe()
    bus.publish("test_event")

    assert queue.empty()


def test_multiple_events_queued_in_order():
    bus: EventBus[str] = EventBus()
    queue: asyncio.Queue[str] = asyncio.Queue()
    bus.subscribe(queue)

    bus.publish("first")
    bus.publish("second")
    bus.publish("third")

    assert queue.get_nowait() == "first"
    assert queue.get_nowait() == "second"
    assert queue.get_nowait() == "third"


class TestEvent(Protocol): ...


@dataclass(kw_only=True, frozen=True)
class TestEventSub(TestEvent):
    name: str


@pytest.fixture
def event_bus():
    return TypedEventBus[TestEvent]()


@pytest.mark.asyncio
async def test_typed_bus_subscribe(event_bus: TypedEventBus[TestEvent]):
    mocked_callback = mock.AsyncMock()
    _ = event_bus.subscribe(TestEventSub, mocked_callback)

    event = TestEventSub(name="test")
    event_bus.publish(event)

    await event_bus.wait_all()

    mocked_callback.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_typed_bus_unsubscribe(event_bus: TypedEventBus[TestEvent]):
    mocked_callback = mock.AsyncMock()
    unsubscribe = event_bus.subscribe(TestEventSub, mocked_callback)

    unsubscribe()
    event = TestEventSub(name="test")
    event_bus.publish(event)
    await event_bus.wait_all()
    mocked_callback.assert_not_called()
