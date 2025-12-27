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
from floorcast.api.subscriptions import Subscription, SubscriptionRegistry
from floorcast.domain.models import Event, Registry

if TYPE_CHECKING:
    from floorcast.domain.ports import EventPublisher
    from floorcast.repositories.event import EventRepository
    from floorcast.services.snapshot import SnapshotService

logger = structlog.get_logger(__name__)

ws_router = APIRouter()


async def route_requests(
    outbound_queue: asyncio.Queue[dict[str, Any]],
    websocket: WebSocket,
    snapshot_service: SnapshotService,
    event_bus: EventPublisher,
) -> None:
    domain_queue = asyncio.Queue[Event]()

    subscriptions = SubscriptionRegistry()

    try:
        async for message in websocket.iter_json():
            msg_type = message.get("type", "unknown")
            logger.debug("received message", type=msg_type)

            if msg_type == "ping":
                await outbound_queue.put({"type": "pong"})
            elif msg_type == "subscribe.live":
                if subscriptions.is_subscribed("live"):
                    logger.warning("already subscribed to live")
                    outbound_queue.put_nowait(
                        {"type": "error", "message": "Already subscribed to live events"}
                    )
                    continue
                subscriptions.subscribe(
                    "live",
                    Subscription(
                        unsubscribe_fn=event_bus.subscribe(domain_queue),
                        task=asyncio.create_task(
                            stream_events(domain_queue, outbound_queue, snapshot_service)
                        ),
                    ),
                )
                outbound_queue.put_nowait({"type": "subscribed"})
            elif msg_type == "unsubscribe.live":
                if not subscriptions.is_subscribed("live"):
                    logger.warning("not subscribed to live")
                    outbound_queue.put_nowait(
                        {"type": "error", "message": "Not subscribed to live events"}
                    )
                    continue
                subscriptions.unsubscribe("live")
                outbound_queue.put_nowait({"type": "unsubscribed"})
            else:
                logger.warning("unknown message type", type=msg_type)
    finally:
        subscriptions.unsubscribe_all()


async def sender(outbound_queue: asyncio.Queue[dict[str, Any]], websocket: WebSocket) -> None:
    while True:
        message = await outbound_queue.get()
        logger.debug("sending message", type=message.get("type"))
        await websocket.send_json(message)


@ws_router.websocket("/events/live")
async def events_live(
    websocket: WebSocket,
    snapshot_service: SnapshotService = Depends(get_snapshot_service_ws),
    event_bus: EventPublisher = Depends(get_event_bus_ws),
) -> None:
    await websocket.accept()
    outbound_queue = asyncio.Queue[dict[str, Any]]()
    logger.info("subscriber connected", queue_id=id(outbound_queue))
    await send_registry(outbound_queue, websocket.app.state.registry)

    try:
        await asyncio.gather(
            route_requests(outbound_queue, websocket, snapshot_service, event_bus),
            sender(outbound_queue, websocket),
        )
    except WebSocketDisconnect:
        pass
    finally:
        logger.info("subscriber disconnected", queue_id=id(outbound_queue))


@ws_router.get("/timeline")
async def events(
    start_time: datetime,
    end_time: datetime | None = None,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
    events_repo: EventRepository = Depends(get_event_repo),
) -> dict[str, Any]:
    from dataclasses import asdict

    snapshot = await snapshot_service.get_state_at(start_time)
    timeline_events = await events_repo.get_timeline_between(
        snapshot.last_event_id or 0, end_time or datetime.now()
    )
    return {"snapshot": asdict(snapshot), "events": [asdict(event) for event in timeline_events]}


async def send_registry(outbound_queue: asyncio.Queue[dict[str, Any]], registry: Registry) -> None:
    await outbound_queue.put({"type": "registry", "registry": registry.to_dict()})


async def stream_events(
    queue: asyncio.Queue[Event],
    outbound_queue: asyncio.Queue[dict[str, Any]],
    snapshot_service: SnapshotService,
) -> None:
    latest_state = await snapshot_service.get_latest_state()
    outbound_queue.put_nowait({"type": "snapshot", "state": latest_state.state})

    latest_event_id = latest_state.last_event_id or 0
    while True:
        event = await queue.get()
        if event.id <= latest_event_id:
            continue
        outbound_queue.put_nowait(
            {"type": "event", "entity_id": event.entity_id, "state": event.state}
        )
