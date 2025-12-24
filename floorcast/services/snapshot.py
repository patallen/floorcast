from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, cast

import structlog

from floorcast.domain.models import Snapshot

if TYPE_CHECKING:
    from floorcast.domain.ports import EventStore, SnapshotStore

logger = structlog.get_logger(__name__)


@dataclass(kw_only=True, frozen=True)
class LatestState:
    state: dict[str, str | None]
    last_event_id: int | None


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

    def _set_cache_state(self, state: dict[str, Any]) -> None:
        self.state_cache = state

    async def get_latest_state(self) -> LatestState:
        latest = await self.snapshot_repo.get_latest()
        state = latest.state if latest else {}
        last_event_id = latest.last_event_id if latest else None
        latest_created_at = latest.created_at if latest else None
        self.last_snapshot_time = latest_created_at or datetime.now(timezone.utc)

        events = await self.event_repo.get_between_id_and_timestamp(
            last_event_id or 0, datetime.now(timezone.utc)
        )
        for event in events:
            state[event.entity_id] = event.state
        return LatestState(state=state, last_event_id=last_event_id)

    async def initialize(self) -> None:
        latest_state = await self.get_latest_state()
        self._set_cache_state(latest_state.state)
        logger.info(
            "rehydrated snapshot state", last_event_id=latest_state.last_event_id
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
