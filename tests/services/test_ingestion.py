import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from floorcast.domain.event_filtering import EntityBlockList
from floorcast.domain.events import EntityStateChanged
from floorcast.domain.models import Event
from floorcast.services.ingestion import IngestionService


def make_event(
    serial: int = 1,
    entity_id: str = "light.living_room",
    state: str = "on",
) -> Event:
    return Event(
        id=serial,
        event_id=uuid.uuid4(),
        external_id=str(uuid.uuid4()),
        state=state,
        timestamp=datetime.now(timezone.utc),
        domain="light",
        entity_id=entity_id,
        event_type="state_changed",
        data={},
    )


async def events_from_list(events: list[Event]):
    """Helper to create an async iterator from a list of events."""
    for event in events:
        yield event


@pytest.fixture
def event_bus():
    return Mock()


@pytest.fixture
def event_repo():
    repo = AsyncMock()
    # Return the event with an ID assigned
    repo.create.side_effect = lambda e: make_event(
        serial=1,
        entity_id=e.entity_id,
        state=e.state,
    )
    return repo


@pytest.fixture
def entity_blocklist():
    return EntityBlockList(blockers=[])


@pytest.fixture
def service(event_bus, event_repo, entity_blocklist):
    return IngestionService(
        event_bus=event_bus,
        event_repo=event_repo,
        entity_blocklist=entity_blocklist,
    )


@pytest.mark.asyncio
async def test_publishes_to_event_bus(service, event_bus):
    event = make_event()
    event_source = events_from_list([event])

    await service.run(event_source=event_source)

    event_bus.publish.assert_called_once()
    published_event = event_bus.publish.call_args[0][0]
    assert isinstance(published_event, EntityStateChanged)
    assert published_event.entity_id == event.entity_id


@pytest.mark.asyncio
async def test_persists_event_to_repo(service, event_repo):
    event = make_event()
    event_source = events_from_list([event])

    await service.run(event_source=event_source)

    event_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_filters_blocked_entities(service, event_bus):
    service._entity_blocklist = EntityBlockList(blockers=["sensor.*"])
    event_source = events_from_list(
        [
            make_event(entity_id="sensor.temperature"),
            make_event(entity_id="light.living_room"),
        ]
    )

    await service.run(event_source=event_source)

    # Only the light event should be published
    event_bus.publish.assert_called_once()
    published_event = event_bus.publish.call_args[0][0]
    assert published_event.entity_id == "light.living_room"


@pytest.mark.asyncio
async def test_processes_multiple_events(service, event_bus, event_repo):
    events = [make_event(serial=i, entity_id=f"light.room_{i}") for i in range(3)]
    event_source = events_from_list(events)

    await service.run(event_source=event_source)

    assert event_bus.publish.call_count == 3
    assert event_repo.create.call_count == 3


@pytest.mark.asyncio
async def test_published_event_contains_domain_event(service, event_bus):
    event = make_event(entity_id="light.kitchen", state="off")
    event_source = events_from_list([event])

    await service.run(event_source=event_source)

    published_event = event_bus.publish.call_args[0][0]
    assert published_event.event.entity_id == "light.kitchen"
    assert published_event.event.state == "off"
