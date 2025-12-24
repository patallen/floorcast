import structlog
from fastapi import APIRouter, Depends
from starlette.websockets import WebSocket, WebSocketDisconnect

from floorcast.api.dependencies import get_event_repo, get_snapshot_service
from floorcast.api.state import Client
from floorcast.repositories.event import EventRepository
from floorcast.services.snapshot import SnapshotService

logger = structlog.get_logger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/events/live")  # type: ignore[misc]
async def events_live(
    websocket: WebSocket,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
    event_repo: EventRepository = Depends(get_event_repo),
) -> None:
    await websocket.accept()
    client = Client()
    websocket.app.state.clients.add(client)
    logger.info("client connected", client_id=client.id)

    try:
        await stream_events(client, websocket, snapshot_service, event_repo)
    except WebSocketDisconnect:
        pass
    finally:
        websocket.app.state.clients.discard(client)
        logger.info("client disconnected", client_id=client.id)


async def stream_events(
    client: Client,
    websocket: WebSocket,
    snapshot_service: SnapshotService,
    event_repo: EventRepository,
) -> None:
    await websocket.send_json({"type": "connected", "client_id": client.id})

    latest_state = await snapshot_service.get_latest_state()
    await websocket.send_json({"type": "snapshot", "state": latest_state.state})

    if latest_state.last_event_id:
        while True:
            event = await client.queue.get()
            if event.id > latest_state.last_event_id:
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
