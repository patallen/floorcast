from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

import structlog

from floorcast.domain.filtering import EntityBlockList, FilteredEventStream

if TYPE_CHECKING:
    from floorcast.domain.models import Event
    from floorcast.domain.ports import EventPublisher, EventStore
    from floorcast.services.snapshot import SnapshotService

logger = structlog.get_logger(__name__)


class IngestionService:
    def __init__(
        self,
        event_bus: EventPublisher,
        event_repo: EventStore,
        snapshot_service: SnapshotService,
        entity_blocklist: EntityBlockList,
    ) -> None:
        self._event_bus = event_bus
        self._event_repo = event_repo
        self._snapshot_service = snapshot_service
        self._entity_blocklist = entity_blocklist
        self._state_cache: dict[str, str | None] = {}

    async def run(self, event_source: AsyncIterator[Event]) -> None:
        logger.info("ingestion started")
        self._state_cache = (await self._snapshot_service.get_latest_state()).state
        event_pipeline = FilteredEventStream(source=event_source, block_list=self._entity_blocklist)
        async for event in event_pipeline:
            event = await self._process_event(event)
            self._event_bus.publish(event)
            if snapshot := await self._snapshot_service.maybe_snapshot(event.id):
                logger.info(
                    "snapshot taken",
                    snapshot_id=snapshot.id,
                    last_event_id=snapshot.last_event_id,
                )

    async def _process_event(self, event: Event) -> Event:
        event = await self._event_repo.create(event)
        logger.info(
            "event persisted",
            event_id=str(event.event_id),
            entity_id=event.entity_id,
            serial=event.id,
            event_type=event.event_type,
        )
        self._state_cache[event.entity_id] = event.state
        return event
