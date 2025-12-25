import uuid
from datetime import datetime, timezone

import pytest

from floorcast.domain.models import Event, Snapshot
from floorcast.infrastructure.db import init_db
from floorcast.repositories.event import EventRepository
from floorcast.repositories.snapshot import SnapshotRepository


@pytest.fixture
async def conn():
    import aiosqlite

    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await init_db(conn)
    yield conn
    await conn.close()


@pytest.fixture
def repo(conn):
    return SnapshotRepository(conn)


@pytest.fixture
def event_repo(conn):
    return EventRepository(conn)


async def create_event(event_repo):
    event = Event(
        domain="light",
        entity_id="light.living_room",
        event_id=uuid.uuid4(),
        event_type="state_changed",
        external_id=str(uuid.uuid4()),
        state="on",
        timestamp=datetime.now(timezone.utc),
        data={},
    )
    return await event_repo.create(event)


@pytest.mark.asyncio
async def test_create_snapshot(repo, event_repo):
    event = await create_event(event_repo)
    snapshot = Snapshot(last_event_id=event.id, state={"light.living_room": "on"})

    result = await repo.create(snapshot)

    assert result.id > 0
    assert result.last_event_id == event.id
    assert result.created_at is not None


@pytest.mark.asyncio
async def test_get_by_id(repo, event_repo):
    event = await create_event(event_repo)
    snapshot = Snapshot(last_event_id=event.id, state={"light.living_room": "on"})
    created = await repo.create(snapshot)

    result = await repo.get_by_id(created.id)

    assert result.id == created.id
    assert result.state == {"light.living_room": "on"}


@pytest.mark.asyncio
async def test_get_by_id_not_found(repo):
    with pytest.raises(ValueError):
        await repo.get_by_id(999)


@pytest.mark.asyncio
async def test_get_latest(repo, event_repo):
    event1 = await create_event(event_repo)
    event2 = await create_event(event_repo)

    await repo.create(Snapshot(last_event_id=event1.id, state={"a": "1"}))
    await repo.create(Snapshot(last_event_id=event2.id, state={"b": "2"}))

    result = await repo.get_latest()

    assert result is not None
    assert result.state == {"b": "2"}


@pytest.mark.asyncio
async def test_get_latest_empty(repo):
    result = await repo.get_latest()
    assert result is None
