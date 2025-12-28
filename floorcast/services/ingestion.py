from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

import structlog

from floorcast.domain.event_filtering import EntityBlockList, FilteredEventStream
from floorcast.domain.events import EntityStateChanged, FCEvent

if TYPE_CHECKING:
    from floorcast.domain.models import Event
    from floorcast.domain.ports import (
        EventPublisher,
        EventStore,
    )

logger = structlog.get_logger(__name__)


class IngestionService:
    def __init__(
        self,
        event_bus: EventPublisher[FCEvent],
        event_repo: EventStore,
        entity_blocklist: EntityBlockList,
    ) -> None:
        self._event_bus = event_bus
        self._event_repo = event_repo
        self._entity_blocklist = entity_blocklist

    async def run(self, event_source: AsyncIterator[Event]) -> None:
        logger.info("ingestion started")
        event_pipeline = FilteredEventStream(source=event_source, block_list=self._entity_blocklist)
        async for event in event_pipeline:
            event = await self._process_event(event)
            self._event_bus.publish(
                EntityStateChanged(entity_id=event.entity_id, state=event.state, event=event)
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
        return event
