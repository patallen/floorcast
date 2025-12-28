from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

from floorcast.domain.events import EntityStateChanged
from floorcast.domain.models import Snapshot

if TYPE_CHECKING:
    from floorcast.domain.ports import SnapshotStore
    from floorcast.domain.snapshot_policies import SnapshotPolicy
    from floorcast.services.state import StateService

logger = structlog.get_logger(__name__)


class SnapshotManager:
    def __init__(
        self,
        snapshot_repo: SnapshotStore,
        state_service: StateService,
        snapshot_policy: SnapshotPolicy,
    ) -> None:
        self._snapshot_repo = snapshot_repo
        self._state_service = state_service
        self._snapshot_policy = snapshot_policy

        # Members related to tracking snapshot state
        self._last_snapshot_time: datetime | None = None
        self._last_snapshot_event_id: int | None = None
        self._state_cache: dict[str, Any] = {}

    async def initialize(self) -> None:
        current_state = await self._state_service.get_state_at(datetime.now(tz=timezone.utc))
        self._last_snapshot_time = current_state.snapshot_time
        self._last_snapshot_event_id = current_state.last_event_id or 0
        self._state_cache = current_state.state

    async def on_entity_state_changed(self, event: EntityStateChanged) -> None:
        self._state_cache[event.event.entity_id] = {
            "value": event.state,
            "unit": event.event.unit,
        }
        last_event_id = event.event.id
        last_snapshot_time = self._last_snapshot_time
        last_snapshot_event_id = self._last_snapshot_event_id or 0
        events_since_snapshot = last_event_id - last_snapshot_event_id

        if not last_snapshot_time or self._snapshot_policy.should_snapshot(
            events_since_snapshot, last_snapshot_time
        ):
            self._last_snapshot_time = datetime.now(tz=timezone.utc)
            snapshot = await self._take_snapshot(event)
            logger.info(
                "snapshot taken",
                snapshot_id=snapshot.id,
                last_event_id=snapshot.last_event_id,
            )

    async def _take_snapshot(self, event: EntityStateChanged) -> Snapshot:
        snapshot = await self._snapshot_repo.create(
            Snapshot(
                state=self._state_cache,
                last_event_id=event.event.id,
            )
        )
        self._last_snapshot_time = snapshot.created_at
        self._last_snapshot_event_id = snapshot.last_event_id
        return snapshot
