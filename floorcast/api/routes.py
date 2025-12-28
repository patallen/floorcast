from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

import structlog
from fastapi import APIRouter, Depends
from starlette.websockets import WebSocket, WebSocketDisconnect

from floorcast.api.dependencies import (
    get_event_bus_ws,
    get_event_repo,
    get_state_service,
    get_state_service_ws,
)
from floorcast.domain.events import EntityStateChanged, FCEvent
from floorcast.domain.models import Registry

if TYPE_CHECKING:
    from floorcast.domain.ports import EventPublisher, StateReconstructor
    from floorcast.repositories.event import EventRepository

logger = structlog.get_logger(__name__)

ws_router = APIRouter()


class WSEventStreamer:
    def __init__(
        self,
        event_bus: EventPublisher[FCEvent],
        state_service: StateReconstructor,
        ws: WebSocket,
        outbound_queue: asyncio.Queue[dict[str, Any]],
    ) -> None:
        self._state_service = state_service
        self._ws = ws
        self._outbound_queue: asyncio.Queue[dict[str, Any]] = outbound_queue
        self._unsubscribe_fn: Callable[[], None] | None = None
        self._event_bus = event_bus

    async def run(self) -> None:
        try:
            async for message in self._ws.iter_json():
                if message.get("type") == "subscribe.live":
                    await self._subscribe_live()
                elif message.get("type") == "unsubscribe.live":
                    self._unsubscribe_live()
                elif message.get("type") == "ping":
                    self._outbound_queue.put_nowait({"type": "pong"})
                else:
                    self._outbound_queue.put_nowait(
                        {"type": "error", "message": "Unknown message type"}
                    )
        finally:
            self._unsubscribe_live()

    async def _live_event_handler(self, event: EntityStateChanged) -> None:
        self._outbound_queue.put_nowait(
            {"type": "event", "entity_id": event.entity_id, "state": event.state}
        )

    async def _subscribe_live(self) -> None:
        state = await self._state_service.get_state_at(datetime.now())
        self._outbound_queue.put_nowait({"type": "snapshot", "state": state.state})

        self._unsubscribe_fn = self._event_bus.subscribe(
            EntityStateChanged, self._live_event_handler
        )

    def _unsubscribe_live(self) -> None:
        if self._unsubscribe_fn is not None:
            self._unsubscribe_fn()


async def sender(outbound_queue: asyncio.Queue[dict[str, Any]], websocket: WebSocket) -> None:
    while True:
        message = await outbound_queue.get()
        logger.debug("sending message", type=message.get("type"))
        await websocket.send_json(message)


@ws_router.websocket("/events/live")
async def events_live(
    websocket: WebSocket,
    state_service: StateReconstructor = Depends(get_state_service_ws),
    event_bus: EventPublisher[FCEvent] = Depends(get_event_bus_ws),
) -> None:
    await websocket.accept()
    outbound_queue = asyncio.Queue[dict[str, Any]]()
    logger.info("subscriber connected", queue_id=id(outbound_queue))
    await send_registry(outbound_queue, websocket.app.state.registry)

    streamer = WSEventStreamer(
        event_bus=event_bus,
        ws=websocket,
        outbound_queue=outbound_queue,
        state_service=state_service,
    )
    try:
        await asyncio.gather(streamer.run(), sender(outbound_queue, websocket))
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
