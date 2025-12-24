from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, AsyncIterator

import structlog

from floorcast.domain.filtering import FilteredEventStream, HasEntityId

if TYPE_CHECKING:
    from floorcast.domain.filtering import EntityBlockList
    from floorcast.domain.models import Event, Subscriber
    from floorcast.domain.ports import EventStore
    from floorcast.services.snapshot import SnapshotService

logger = structlog.get_logger(__name__)


async def run_ingestion[T: HasEntityId](
    subscribers: set[Subscriber],
    event_repo: EventStore,
    snapshot_service: SnapshotService,
    block_list: EntityBlockList,
    event_source: AbstractAsyncContextManager[AsyncIterator[T]],
    event_mapper: Callable[[T], Awaitable[Event]],
) -> None:
    await snapshot_service.initialize()
    logger.info("snapshot service initialized")

    async with event_source as source:
        event_pipeline = FilteredEventStream(source=source, block_list=block_list)

        async for raw_event in event_pipeline:
            event = await event_mapper(raw_event)
            event = await event_repo.create(event)
            logger.info(
                "event persisted",
                event_id=str(event.event_id),
                entity_id=event.entity_id,
                serial=event.id,
                event_type=event.event_type,
            )
            snapshot_service.update_state(event.entity_id, event.state)
            for subscriber in subscribers:
                subscriber.queue.put_nowait(event)
            if snapshot := await snapshot_service.maybe_snapshot(event.id):
                logger.info(
                    "snapshot taken",
                    snapshot_id=snapshot.id,
                    last_event_id=snapshot.last_event_id,
                )
