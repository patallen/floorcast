import structlog
from fastapi import APIRouter, Depends
from starlette.websockets import WebSocket, WebSocketDisconnect

from floorcast.api.dependencies import get_event_repo, get_snapshot_service
from floorcast.models import Subscriber
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
    subscriber = Subscriber()
    websocket.app.state.subscribers.add(subscriber)
    logger.info("subscriber connected", subscriber_id=subscriber.id)

    try:
        await stream_events(subscriber, websocket, snapshot_service, event_repo)
    except WebSocketDisconnect:
        pass
    finally:
        websocket.app.state.subscribers.discard(subscriber)
        logger.info("subscriber disconnected", subscriber_id=subscriber.id)


async def stream_events(
    subscriber: Subscriber,
    websocket: WebSocket,
    snapshot_service: SnapshotService,
    event_repo: EventRepository,
) -> None:
    await websocket.send_json({"type": "connected", "subscriber_id": subscriber.id})

    latest_state = await snapshot_service.get_latest_state()
    await websocket.send_json({"type": "snapshot", "state": latest_state.state})

    if latest_state.last_event_id:
        while True:
            event = await subscriber.queue.get()
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
        event = await subscriber.queue.get()
        await websocket.send_json(
            {"type": "event", "entity_id": event.entity_id, "state": event.state}
        )
