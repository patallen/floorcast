from datetime import datetime, timedelta, timezone

import structlog

from floorcast.models import Snapshot
from floorcast.repository import EventRepository, SnapshotRepository

logger = structlog.get_logger(__name__)


class SnapshotService:
    def __init__(
        self,
        snapshot_repo: SnapshotRepository,
        event_repo: EventRepository,
        interval_seconds: int,
    ):
        self.snapshot_repo = snapshot_repo
        self.event_repo = event_repo
        self.interval_seconds = interval_seconds
        self.state_cache = {}
        self.last_snapshot_time = datetime.now(timezone.utc)

    async def initialize(self):
        latest = await self.snapshot_repo.get_latest()
        last_event_id = latest.last_event_id if latest else None
        self.last_snapshot_time = (
            latest.created_at if latest else datetime.now(timezone.utc)
        )

        events = await self.event_repo.get_between_id_and_timestamp(
            last_event_id, datetime.now(timezone.utc)
        )
        for event in events:
            self.update_state(event.entity_id, event.state)

        logger.info(
            "rehydrated snapshot state",
            last_snapshot_id=latest.id if latest else None,
            event_count=len(events),
        )

    def update_state(self, entity_id: str, state: str | None):
        self.state_cache[entity_id] = state

    async def maybe_snapshot(self, event_id: int) -> Snapshot | None:
        if datetime.now(timezone.utc) - self.last_snapshot_time <= timedelta(
            seconds=self.interval_seconds
        ):
            return None
        snapshot = Snapshot(last_event_id=event_id, state=self.state_cache)
        snapshot = await self.snapshot_repo.create(snapshot)
        self.last_snapshot_time = snapshot.created_at
        return snapshot
