from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, Depends
from starlette.websockets import WebSocket, WebSocketDisconnect

from floorcast.api.dependencies import (
    get_event_bus_ws,
    get_event_repo,
    get_snapshot_service,
    get_snapshot_service_ws,
)
from floorcast.api.subscriber import SubscriberChannel
from floorcast.domain.models import Event, Registry

if TYPE_CHECKING:
    from floorcast.domain.ports import EventPublisher
    from floorcast.repositories.event import EventRepository
    from floorcast.services.snapshot import SnapshotService

logger = structlog.get_logger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/events/live")
async def events_live(
    websocket: WebSocket,
    snapshot_service: SnapshotService = Depends(get_snapshot_service_ws),
    event_bus: EventPublisher = Depends(get_event_bus_ws),
) -> None:
    await websocket.accept()
    queue = asyncio.Queue[Event]()
    unsubscribe = event_bus.subscribe(queue)
    channel = SubscriberChannel(websocket)
    logger.info("subscriber connected", queue_id=id(queue))

    try:
        await send_registry(channel, websocket.app.state.registry)
        await stream_events(queue, channel, snapshot_service)
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe()
        logger.info("subscriber disconnected", queue_id=id(queue))


@ws_router.get("/timeline")
async def events(
    start_time: datetime,
    end_time: datetime | None = None,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
    events_repo: EventRepository = Depends(get_event_repo),
) -> dict[str, Any]:
    from dataclasses import asdict

    snapshot = await snapshot_service.get_state_at(start_time)
    timeline_events = await events_repo.get_between_id_and_timestamp(
        snapshot.last_event_id or 0, end_time or datetime.now()
    )
    return {"snapshot": asdict(snapshot), "events": [asdict(event) for event in timeline_events]}


async def send_registry(channel: SubscriberChannel, registry: Registry) -> None:
    await channel.send_registry(registry.to_dict())


async def stream_events(
    queue: asyncio.Queue[Event],
    channel: SubscriberChannel,
    snapshot_service: SnapshotService,
) -> None:
    await channel.send_connected(id(queue))
    latest_state = await snapshot_service.get_latest_state()
    await channel.send_snapshot(latest_state.state)

    if latest_state.last_event_id:
        while True:
            event = await queue.get()
            if event.id > latest_state.last_event_id:
                await channel.send_event(event.entity_id, event.state)
                break

    while True:
        event = await queue.get()
        await channel.send_event(event.entity_id, event.state)
