from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, Depends
from starlette.websockets import WebSocket, WebSocketDisconnect

from floorcast.api.dependencies import (
    get_event_repo,
    get_state_service,
    get_websocket_service_ws,
)
from floorcast.domain.websocket import WSConnection, WSMessage

if TYPE_CHECKING:
    from floorcast.domain.ports import EventStore
    from floorcast.services.state import StateService
    from floorcast.services.websocket import WebsocketService

logger = structlog.get_logger(__name__)

ws_router = APIRouter()


@ws_router.get("/timeline")
async def events(
    start_time: datetime,
    end_time: datetime | None = None,
    state_service: StateService = Depends(get_state_service),
    events_repo: EventStore = Depends(get_event_repo),
) -> dict[str, Any]:
    snapshot = await state_service.get_state_at(start_time)
    timeline_events = await events_repo.get_timeline_between(
        snapshot.last_event_id or 0, end_time or datetime.now(tz=timezone.utc)
    )
    return {"snapshot": asdict(snapshot), "events": [asdict(event) for event in timeline_events]}


def serialize(message: WSMessage) -> dict[str, Any]:
    if message.type == "registry":
        return {"type": message.type, "registry": message.data}
    if message.type == "snapshot":
        return {"type": message.type, "state": message.data}
    if message.type == "entity.state_change":
        assert isinstance(message.data, dict)
        data = message.data
        return {
            "type": "event",
            "entity_id": data["entity_id"],
            "state": data["state"],
            "unit": data["unit"],
            "timestamp": data["timestamp"],
            "id": data["id"],
        }
    if message.type == "pong":
        return {"type": message.type}
    raise ValueError(f"Unknown message type: {message.type}")


async def sender(conn: WSConnection, ws: WebSocket) -> None:
    while True:
        message = await conn.queue.get()
        serialized = serialize(message)
        await ws.send_json(serialized)


async def receiver(conn: WSConnection, ws: WebSocket, service: WebsocketService) -> None:
    async for message in ws.iter_json():
        service.send_message(conn, WSMessage(type=message["type"], data=message.get("data")))


@ws_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    websocket_service: WebsocketService = Depends(get_websocket_service_ws),
) -> None:
    await websocket.accept()
    ws_conn = websocket_service.connect()
    logger.info("subscriber connected", connection=str(ws_conn.id))
    await websocket_service.request_registry(ws_conn)
    await websocket_service.request_snapshot(ws_conn)
    try:
        await asyncio.gather(
            sender(ws_conn, websocket), receiver(ws_conn, websocket, websocket_service)
        )
    except WebSocketDisconnect:
        pass
    finally:
        websocket_service.disconnect(ws_conn)
        logger.info("subscriber disconnected", connection=str(ws_conn.id))
