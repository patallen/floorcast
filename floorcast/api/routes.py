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
    get_state_service,
    get_state_service_ws,
)
from floorcast.api.subscriptions import Subscription, SubscriptionRegistry
from floorcast.common.aio import create_logged_task
from floorcast.domain.models import Event, Registry
from floorcast.services.state import StateService

if TYPE_CHECKING:
    from floorcast.domain.ports import EventPublisher, StateReconstructor
    from floorcast.repositories.event import EventRepository

logger = structlog.get_logger(__name__)

ws_router = APIRouter()


async def route_requests(
    outbound_queue: asyncio.Queue[dict[str, Any]],
    websocket: WebSocket,
    state_service: StateReconstructor,
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
                        task=create_logged_task(
                            stream_events(domain_queue, outbound_queue, state_service)
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
    state_service: StateService = Depends(get_state_service_ws),
    event_bus: EventPublisher = Depends(get_event_bus_ws),
) -> None:
    await websocket.accept()
    outbound_queue = asyncio.Queue[dict[str, Any]]()
    logger.info("subscriber connected", queue_id=id(outbound_queue))
    await send_registry(outbound_queue, websocket.app.state.registry)

    try:
        await asyncio.gather(
            route_requests(outbound_queue, websocket, state_service, event_bus),
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
    state_service: StateReconstructor = Depends(get_state_service),
    events_repo: EventRepository = Depends(get_event_repo),
) -> dict[str, Any]:
    from dataclasses import asdict

    snapshot = await state_service.get_state_at(start_time)
    timeline_events = await events_repo.get_timeline_between(
        snapshot.last_event_id or 0, end_time or datetime.now()
    )
    return {"snapshot": asdict(snapshot), "events": [asdict(event) for event in timeline_events]}


async def send_registry(outbound_queue: asyncio.Queue[dict[str, Any]], registry: Registry) -> None:
    await outbound_queue.put({"type": "registry", "registry": registry.to_dict()})


async def stream_events(
    queue: asyncio.Queue[Event],
    outbound_queue: asyncio.Queue[dict[str, Any]],
    state_service: StateReconstructor,
) -> None:
    latest_state = await state_service.get_state_at(end_time=datetime.now())
    logger.debug(
        "sending snapshot",
        key_count=len(latest_state.state),
        sample_keys=list(latest_state.state)[:5],
    )
    outbound_queue.put_nowait({"type": "snapshot", "state": latest_state.state})

    latest_event_id = latest_state.last_event_id or 0
    while True:
        event = await queue.get()
        if event.id <= latest_event_id:
            continue
        outbound_queue.put_nowait(
            {"type": "event", "entity_id": event.entity_id, "state": event.state}
        )
