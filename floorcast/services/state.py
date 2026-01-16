from __future__ import annotations

import copy
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from floorcast.domain.models import ConstructedState, Event, Snapshot

if TYPE_CHECKING:
    from floorcast.domain.ports import EventStore, SnapshotStore

logger = structlog.get_logger(__name__)


class StateService:
    def __init__(self, snapshot_repo: SnapshotStore, event_repo: EventStore) -> None:
        self._snapshot_repo = snapshot_repo
        self._event_repo = event_repo

    async def get_state_at(self, end_time: datetime) -> ConstructedState:
        import time

        start = time.time()
        snapshot = await self._snapshot_repo.get_before_timestamp(end_time)
        snapshot_time = time.time()
        logger.debug("StateService loaded snapshot", snapshot_id=snapshot.id if snapshot else None)
        last_event_id = snapshot.last_event_id if snapshot else 0
        events = await self._event_repo.get_between_id_and_timestamp(last_event_id, end_time)
        events_time = time.time()
        logger.debug("StateService loaded events", events_count=len(events))
        reconstructed_state = self._reconstruct_state(snapshot, events)
        reconstruct_state_time = time.time()
        logger.info(
            "get_state_at timings",
            total=reconstruct_state_time - events_time,
            snapshot=snapshot_time - start,
            timeline=events_time - snapshot_time,
        )
        logger.debug(
            "StateService reconstructed state",
            end_time=end_time.isoformat(),
            snapshot_id=last_event_id,
            last_event_id=reconstructed_state.last_event_id,
            key_count=len(reconstructed_state.state),
            events_applied=len(events),
        )
        return reconstructed_state

    @staticmethod
    def _reconstruct_state(snapshot: Snapshot | None, events: list[Event]) -> ConstructedState:
        state = copy.copy(snapshot.state if snapshot else {})
        snapshot_id = snapshot.id if snapshot else None
        snapshot_time = snapshot.created_at if snapshot else None
        last_event_id = snapshot.last_event_id if snapshot else None
        for event in events:
            state[event.entity_id] = {
                "value": event.state,
                "unit": event.unit,
            }
            last_event_id = event.id
        return ConstructedState(
            state=state,
            last_event_id=last_event_id,
            snapshot_id=snapshot_id,
            snapshot_time=snapshot_time,
        )
