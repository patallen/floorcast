from datetime import datetime, timedelta, timezone
from typing import Protocol, cast

import structlog

from floorcast.models import Event, Snapshot

logger = structlog.get_logger(__name__)


class SnapshotStore(Protocol):
    async def create(self, snapshot: Snapshot) -> Snapshot: ...
    async def get_latest(self) -> Snapshot | None: ...


class EventStore(Protocol):
    async def get_between_id_and_timestamp(
        self, event_id: int, timestamp: datetime
    ) -> list[Event]: ...


class SnapshotService:
    def __init__(
        self,
        snapshot_repo: SnapshotStore,
        event_repo: EventStore,
        interval_seconds: int,
    ) -> None:
        self.snapshot_repo = snapshot_repo
        self.event_repo = event_repo
        self.interval_seconds = interval_seconds
        self.state_cache: dict[str, str | None] = {}
        self.last_snapshot_time = datetime.now(timezone.utc)

    async def initialize(self) -> None:
        latest = await self.snapshot_repo.get_latest()
        last_event_id = latest.last_event_id if latest else None
        latest_created_at = latest.created_at if latest else None
        self.last_snapshot_time = latest_created_at or datetime.now(timezone.utc)

        events = await self.event_repo.get_between_id_and_timestamp(
            last_event_id or 0, datetime.now(timezone.utc)
        )
        for event in events:
            self.update_state(event.entity_id, event.state)

        logger.info(
            "rehydrated snapshot state",
            last_snapshot_id=latest.id if latest else None,
            event_count=len(events),
        )

    def update_state(self, entity_id: str, state: str | None) -> None:
        self.state_cache[entity_id] = state

    async def maybe_snapshot(self, event_id: int) -> Snapshot | None:
        if datetime.now(timezone.utc) - self.last_snapshot_time <= timedelta(
            seconds=self.interval_seconds
        ):
            return None
        snapshot = Snapshot(last_event_id=event_id, state=self.state_cache)
        snapshot = await self.snapshot_repo.create(snapshot)
        self.last_snapshot_time = cast(datetime, snapshot.created_at)
        return snapshot
