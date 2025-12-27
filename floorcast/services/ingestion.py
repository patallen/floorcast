from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, AsyncIterator

import structlog

from floorcast.domain.event_filtering import EntityBlockList, FilteredEventStream
from floorcast.domain.models import Snapshot

if TYPE_CHECKING:
    from floorcast.domain.models import ConstructedState, Event
    from floorcast.domain.ports import (
        EventPublisher,
        EventStore,
        SnapshotPolicy,
        SnapshotStore,
        StateReconstructor,
    )

logger = structlog.get_logger(__name__)


class StateCache:
    def __init__(self, state: dict[str, Any], last_event_id: int = 0) -> None:
        self._state: dict[str, str | None] = state
        self._last_event_id: int = last_event_id

    def get_state(self) -> dict[str, str | None]:
        return self._state

    def get_latest_event_id(self) -> int:
        return self._last_event_id

    def update(self, event: Event) -> None:
        self._state[event.entity_id] = event.state
        self._last_event_id = event.id

    @classmethod
    def from_constructed_state(cls, constructed_state: ConstructedState) -> "StateCache":
        return cls(
            state=constructed_state.state,
            last_event_id=constructed_state.last_event_id or 0,
        )


class IngestionService:
    def __init__(
        self,
        event_bus: EventPublisher,
        event_repo: EventStore,
        state_service: StateReconstructor,
        snapshot_repo: SnapshotStore,
        entity_blocklist: EntityBlockList,
        snapshot_policy: SnapshotPolicy,
    ) -> None:
        self._event_bus = event_bus
        self._event_repo = event_repo
        self._snapshot_repo = snapshot_repo
        self._state_service = state_service
        self._entity_blocklist = entity_blocklist
        self._snapshot_policy = snapshot_policy

        # Members related to tracking snapshot state
        self._last_snapshot_time: datetime | None = None
        self._last_snapshot_event_id: int | None = None
        self._state_cache: StateCache = StateCache({})

    async def _initialize(self) -> None:
        current_state = await self._state_service.get_state_at(datetime.now())
        self._last_snapshot_time = current_state.snapshot_time
        self._last_snapshot_event_id = current_state.last_event_id or 0
        self._state_cache = StateCache.from_constructed_state(current_state)

    async def run(self, event_source: AsyncIterator[Event]) -> None:
        await self._initialize()

        logger.info("ingestion started")
        event_pipeline = FilteredEventStream(source=event_source, block_list=self._entity_blocklist)
        async for event in event_pipeline:
            event = await self._process_event(event)
            self._event_bus.publish(event)
            self._state_cache.update(event)
            await self._maybe_snapshot()

    async def _process_event(self, event: Event) -> Event:
        event = await self._event_repo.create(event)
        logger.info(
            "event persisted",
            event_id=str(event.event_id),
            entity_id=event.entity_id,
            serial=event.id,
            event_type=event.event_type,
        )
        return event

    async def _maybe_snapshot(self) -> None:
        last_event_id = self._state_cache.get_latest_event_id()
        last_snapshot_time = self._last_snapshot_time
        last_snapshot_event_id = self._last_snapshot_event_id or 0
        events_since_snapshot = last_event_id - last_snapshot_event_id

        if not last_snapshot_time or self._snapshot_policy.should_snapshot(
            events_since_snapshot, last_snapshot_time
        ):
            snapshot = await self._take_snapshot()
            logger.info(
                "snapshot taken",
                snapshot_id=snapshot.id,
                last_event_id=snapshot.last_event_id,
            )

    async def _take_snapshot(self) -> Snapshot:
        snapshot = await self._snapshot_repo.create(
            Snapshot(
                state=self._state_cache.get_state(),
                last_event_id=self._state_cache.get_latest_event_id(),
            )
        )
        self._last_snapshot_time = snapshot.created_at
        self._last_snapshot_event_id = snapshot.last_event_id
        return snapshot
