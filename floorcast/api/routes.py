from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends
from starlette.websockets import WebSocket, WebSocketDisconnect

from floorcast.api.dependencies import get_event_repo, get_snapshot_repo
from floorcast.api.state import Client
from floorcast.repositories.event import EventRepository
from floorcast.repositories.snapshot import SnapshotRepository

logger = structlog.get_logger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/events/live")  # type: ignore[misc]
async def events_live(
    websocket: WebSocket,
    snapshot_repo: SnapshotRepository = Depends(get_snapshot_repo),
    event_repo: EventRepository = Depends(get_event_repo),
) -> None:
    await websocket.accept()
    client = Client()
    websocket.app.state.clients.add(client)
    logger.info("client connected", client_id=client.id)

    try:
        await stream_events(client, websocket, snapshot_repo, event_repo)
    except WebSocketDisconnect:
        pass
    finally:
        websocket.app.state.clients.discard(client)
        logger.info("client disconnected", client_id=client.id)


async def stream_events(
    client: Client,
    websocket: WebSocket,
    snapshot_repo: SnapshotRepository,
    event_repo: EventRepository,
) -> None:
    await websocket.send_json({"type": "connected", "client_id": client.id})

    state = {}
    latest_snapshot = await snapshot_repo.get_latest()
    last_event_id = None
    if latest_snapshot:
        state = latest_snapshot.state
        events = await event_repo.get_between_id_and_timestamp(
            latest_snapshot.last_event_id, datetime.now(timezone.utc)
        )
        for event in events:
            state[event.entity_id] = event.state
            last_event_id = event.id

    await websocket.send_json({"type": "snapshot", "state": state})

    if last_event_id:
        while True:
            event = await client.queue.get()
            if event.id > last_event_id:
                await websocket.send_json(
                    {
                        "type": "event",
                        "entity_id": event.entity_id,
                        "state": event.state,
                    }
                )
                break

    while True:
        event = await client.queue.get()
        await websocket.send_json(
            {"type": "event", "entity_id": event.entity_id, "state": event.state}
        )
