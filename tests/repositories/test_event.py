import uuid
from datetime import datetime, timezone

import pytest

from floorcast.domain.models import Event
from floorcast.repositories.event import EventRepository


@pytest.fixture
def repo(conn):
    return EventRepository(conn)


def make_event(**overrides):
    defaults = {
        "domain": "light",
        "entity_id": "light.living_room",
        "event_id": uuid.uuid4(),
        "event_type": "state_changed",
        "external_id": str(uuid.uuid4()),
        "state": "on",
        "timestamp": datetime.now(timezone.utc),
        "data": {},
    }
    return Event(**{**defaults, **overrides})


@pytest.mark.asyncio
async def test_create_event(repo):
    event = make_event()
    result = await repo.create(event)

    assert result.id > 0
    assert result.entity_id == event.entity_id


@pytest.mark.asyncio
async def test_get_by_id(repo):
    event = make_event()
    created = await repo.create(event)

    result = await repo.get_by_id(created.id)

    assert result is not None
    assert result.id == created.id
    assert result.entity_id == event.entity_id


@pytest.mark.asyncio
async def test_get_by_id_not_found(repo):
    result = await repo.get_by_id(999)
    assert result is None


@pytest.mark.asyncio
async def test_get_between_id_and_timestamp(repo):
    event1 = make_event(timestamp=datetime.now(timezone.utc))
    event2 = make_event(timestamp=datetime.now(timezone.utc))
    event3 = make_event(timestamp=datetime.now(timezone.utc))

    await repo.create(event1)
    created2 = await repo.create(event2)
    await repo.create(event3)

    future = datetime(2099, 1, 1, tzinfo=timezone.utc)
    results = await repo.get_between_id_and_timestamp(created2.timestamp, future)

    assert len(results) == 1
    assert results[0].id == event3.id


@pytest.mark.asyncio
async def test_create_duplicate_external_id_returns_original_event(repo):
    external_id = str(uuid.uuid4())
    event0 = make_event(external_id=external_id)
    event1 = make_event(external_id="fake-id")
    event2 = make_event(external_id=external_id)

    res0 = await repo.create(event0)
    res1 = await repo.create(event1)
    res2 = await repo.create(event2)

    assert res0.id == 1
    assert res1.id == 2
    assert res2.id == 1
