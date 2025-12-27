from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from floorcast.domain.models import CompactEvent, Snapshot
from floorcast.domain.ports import EventStore, SnapshotStore
from floorcast.services.snapshot import SnapshotService


@pytest.fixture
def snapshot_repo():
    return AsyncMock(spec=SnapshotStore)


@pytest.fixture
def event_repo():
    return AsyncMock(spec=EventStore)


@pytest.fixture
def service(snapshot_repo, event_repo):
    return SnapshotService(snapshot_repo, event_repo, interval_seconds=60)


def make_compact_event(entity_id: str, state: str, id: int = 1) -> CompactEvent:
    return CompactEvent(
        id=id,
        entity_id=entity_id,
        state=state,
        timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
    )


class TestInitialize:
    @pytest.mark.asyncio
    async def test_initializes_cache_from_latest_snapshot(self, service, snapshot_repo, event_repo):
        snapshot_repo.get_latest.return_value = Snapshot(
            id=1,
            last_event_id=5,
            state={"light.living_room": "on"},
            created_at=datetime.now(timezone.utc),
        )
        event_repo.get_timeline_between.return_value = []

        await service.initialize()

        assert service.state_cache == {"light.living_room": "on"}

    @pytest.mark.asyncio
    async def test_applies_events_after_snapshot(self, service, snapshot_repo, event_repo):
        snapshot_repo.get_latest.return_value = Snapshot(
            id=1,
            last_event_id=5,
            state={"light.living_room": "on"},
            created_at=datetime.now(timezone.utc),
        )
        event_repo.get_timeline_between.return_value = [
            make_compact_event("light.living_room", "off", id=6),
            make_compact_event("light.bedroom", "on", id=7),
        ]

        await service.initialize()

        assert service.state_cache == {"light.living_room": "off", "light.bedroom": "on"}

    @pytest.mark.asyncio
    async def test_initializes_empty_when_no_snapshot(self, service, snapshot_repo, event_repo):
        snapshot_repo.get_latest.return_value = None
        event_repo.get_timeline_between.return_value = []

        await service.initialize()

        assert service.state_cache == {}


class TestUpdateState:
    def test_updates_cache(self, service):
        service.update_state("light.living_room", "on")

        assert service.state_cache["light.living_room"] == "on"

    def test_updates_existing_entry(self, service):
        service.state_cache["light.living_room"] = "on"

        service.update_state("light.living_room", "off")

        assert service.state_cache["light.living_room"] == "off"

    def test_handles_none_state(self, service):
        service.update_state("light.living_room", None)

        assert service.state_cache["light.living_room"] is None


class TestMaybeSnapshot:
    @pytest.mark.asyncio
    async def test_creates_snapshot_when_interval_passed(self, service, snapshot_repo):
        service.last_snapshot_time = datetime.now(timezone.utc) - timedelta(seconds=120)
        service.state_cache = {"light.living_room": "on"}
        snapshot_repo.create.return_value = Snapshot(
            id=1,
            last_event_id=10,
            state={"light.living_room": "on"},
            created_at=datetime.now(timezone.utc),
        )

        result = await service.maybe_snapshot(event_id=10)

        assert result is not None
        assert result.last_event_id == 10
        snapshot_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_snapshot_when_interval_not_passed(self, service, snapshot_repo):
        service.last_snapshot_time = datetime.now(timezone.utc) - timedelta(seconds=30)

        result = await service.maybe_snapshot(event_id=10)

        assert result is None
        snapshot_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_updates_last_snapshot_time(self, service, snapshot_repo):
        service.last_snapshot_time = datetime.now(timezone.utc) - timedelta(seconds=120)
        service.state_cache = {}
        new_time = datetime.now(timezone.utc)
        snapshot_repo.create.return_value = Snapshot(
            id=1, last_event_id=10, state={}, created_at=new_time
        )

        await service.maybe_snapshot(event_id=10)

        assert service.last_snapshot_time == new_time


class TestGetLatestState:
    @pytest.mark.asyncio
    async def test_returns_snapshot_state(self, service, snapshot_repo, event_repo):
        snapshot_repo.get_latest.return_value = Snapshot(
            id=1,
            last_event_id=5,
            state={"light.living_room": "on"},
            created_at=datetime.now(timezone.utc),
        )
        event_repo.get_timeline_between.return_value = []

        result = await service.get_latest_state()

        assert result.state == {"light.living_room": "on"}
        assert result.last_event_id == 5

    @pytest.mark.asyncio
    async def test_merges_events_after_snapshot(self, service, snapshot_repo, event_repo):
        snapshot_repo.get_latest.return_value = Snapshot(
            id=1,
            last_event_id=5,
            state={"light.living_room": "on"},
            created_at=datetime.now(timezone.utc),
        )
        event_repo.get_timeline_between.return_value = [
            make_compact_event("light.living_room", "off", id=6),
        ]

        result = await service.get_latest_state()

        assert result.state == {"light.living_room": "off"}

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_snapshot(self, service, snapshot_repo, event_repo):
        snapshot_repo.get_latest.return_value = None
        event_repo.get_timeline_between.return_value = []

        result = await service.get_latest_state()

        assert result.state == {}
        assert result.last_event_id is None


class TestGetStateAt:
    @pytest.mark.asyncio
    async def test_returns_state_at_timestamp(self, service, snapshot_repo, event_repo):
        target_time = datetime(2021, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        snapshot_repo.get_before_timestamp.return_value = Snapshot(
            id=1,
            last_event_id=5,
            state={"light.living_room": "on"},
            created_at=datetime(2021, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
        )
        event_repo.get_timeline_between.return_value = [
            make_compact_event("light.bedroom", "on", id=6),
        ]

        result = await service.get_state_at(target_time)

        assert result.state == {"light.living_room": "on", "light.bedroom": "on"}
        snapshot_repo.get_before_timestamp.assert_called_once_with(target_time)

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_snapshot_before_timestamp(
        self, service, snapshot_repo, event_repo
    ):
        target_time = datetime(2021, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        snapshot_repo.get_before_timestamp.return_value = None
        event_repo.get_timeline_between.return_value = []

        result = await service.get_state_at(target_time)

        assert result.state == {}
        assert result.last_event_id is None
