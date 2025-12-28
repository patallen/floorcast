import uuid
from datetime import datetime, timezone

import pytest

from floorcast.domain.models import Event, Snapshot
from floorcast.repositories.event import EventRepository
from floorcast.repositories.snapshot import SnapshotRepository


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


@pytest.mark.asyncio
async def test_get_before_timestamp_exists(conn, repo, event_repo):
    snapshot1 = Snapshot(last_event_id=1, state={"a": "1"})
    snapshot2 = Snapshot(last_event_id=2, state={"b": "2"})
    snapshot3 = Snapshot(last_event_id=3, state={"c": "3"})

    await repo.create(snapshot1)
    await repo.create(snapshot2)
    await repo.create(snapshot3)

    await conn.execute(
        "UPDATE snapshots SET created_at = '2021-01-01 00:00:00' WHERE id = ?;", (snapshot1.id,)
    )
    await conn.execute(
        "UPDATE snapshots SET created_at = '2021-01-02 00:00:00' WHERE id = ?;", (snapshot2.id,)
    )
    await conn.execute(
        "UPDATE snapshots SET created_at = '2021-01-03 00:00:00' WHERE id = ?;", (snapshot3.id,)
    )
    await conn.commit()

    result = await repo.get_before_timestamp(datetime(2021, 1, 2))
    assert result.id == snapshot1.id


@pytest.mark.asyncio
async def test_get_before_timestamp_returns_none_if_not_exists(conn, repo, event_repo):
    snapshot1 = Snapshot(last_event_id=1, state={"a": "1"})
    await repo.create(snapshot1)

    await conn.execute(
        "UPDATE snapshots SET created_at = '2025-01-01 00:00:00' WHERE id = ?;", (snapshot1.id,)
    )
    await conn.commit()

    # timestamp is before the first available snapshot
    result = await repo.get_before_timestamp(datetime(2021, 1, 2))
    assert result is None
