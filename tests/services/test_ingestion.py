import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from floorcast.domain.event_filtering import EntityBlockList
from floorcast.domain.models import ConstructedState, Event, Snapshot
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


def make_constructed_state() -> ConstructedState:
    return ConstructedState(
        state={},
        last_event_id=0,
        snapshot_id=1,
        snapshot_time=datetime.now(timezone.utc),
    )


def make_snapshot() -> Snapshot:
    return Snapshot(
        id=1,
        state={},
        last_event_id=1,
        created_at=datetime.now(timezone.utc),
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
def state_service():
    service = AsyncMock()
    service.get_state_at.return_value = make_constructed_state()
    return service


@pytest.fixture
def snapshot_repo():
    repo = AsyncMock()
    repo.create.return_value = make_snapshot()
    return repo


@pytest.fixture
def snapshot_policy():
    policy = Mock()
    policy.should_snapshot.return_value = False
    return policy


@pytest.fixture
def entity_blocklist():
    return EntityBlockList(blockers=[])


@pytest.fixture
def service(event_bus, event_repo, state_service, snapshot_repo, snapshot_policy, entity_blocklist):
    return IngestionService(
        event_bus=event_bus,
        event_repo=event_repo,
        snapshot_repo=snapshot_repo,
        state_service=state_service,
        entity_blocklist=entity_blocklist,
        snapshot_policy=snapshot_policy,
    )


@pytest.mark.asyncio
async def test_publishes_to_event_bus(service, event_bus):
    event = make_event()
    event_source = events_from_list([event])

    await service.run(event_source=event_source)

    event_bus.publish.assert_called_once()
    published_event = event_bus.publish.call_args[0][0]
    assert published_event.entity_id == event.entity_id


@pytest.mark.asyncio
async def test_persists_event_to_repo(service, event_repo):
    event = make_event()
    event_source = events_from_list([event])

    await service.run(event_source=event_source)

    event_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_takes_snapshot_when_policy_approves(service, snapshot_repo, snapshot_policy):
    snapshot_policy.should_snapshot.return_value = True
    event_source = events_from_list([make_event()])

    await service.run(event_source=event_source)

    snapshot_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_does_not_snapshot_when_policy_rejects(service, snapshot_repo, snapshot_policy):
    snapshot_policy.should_snapshot.return_value = False
    event_source = events_from_list([make_event()])

    await service.run(event_source=event_source)

    snapshot_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_takes_snapshot_on_cold_start(
    snapshot_repo, snapshot_policy, state_service, event_bus, event_repo
):
    # Cold start: no prior snapshot
    state_service.get_state_at.return_value = ConstructedState(
        state={},
        last_event_id=0,
        snapshot_id=None,
        snapshot_time=None,
    )
    snapshot_policy.should_snapshot.return_value = False  # policy says no, but cold start overrides

    service = IngestionService(
        event_bus=event_bus,
        event_repo=event_repo,
        snapshot_repo=snapshot_repo,
        state_service=state_service,
        entity_blocklist=EntityBlockList(blockers=[]),
        snapshot_policy=snapshot_policy,
    )
    event_source = events_from_list([make_event()])

    await service.run(event_source=event_source)

    # Should snapshot despite policy saying no, because it's cold start
    snapshot_repo.create.assert_called_once()


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
