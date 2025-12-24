import structlog
from fastapi import APIRouter, Depends
from starlette.websockets import WebSocket, WebSocketDisconnect

from floorcast.api.dependencies import get_snapshot_service
from floorcast.api.subscriber import SubscriberChannel
from floorcast.domain.models import Subscriber
from floorcast.services.snapshot import SnapshotService

logger = structlog.get_logger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/events/live")  # type: ignore[misc]
async def events_live(
    websocket: WebSocket,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
) -> None:
    await websocket.accept()
    subscriber = Subscriber()
    websocket.app.state.subscribers.add(subscriber)
    channel = SubscriberChannel(websocket)
    logger.info("subscriber connected", subscriber_id=subscriber.id)

    try:
        await stream_events(subscriber, channel, snapshot_service)
    except WebSocketDisconnect:
        pass
    finally:
        websocket.app.state.subscribers.discard(subscriber)
        logger.info("subscriber disconnected", subscriber_id=subscriber.id)


async def stream_events(
    subscriber: Subscriber,
    channel: SubscriberChannel,
    snapshot_service: SnapshotService,
) -> None:
    await channel.send_connected(subscriber.id)
    latest_state = await snapshot_service.get_latest_state()
    await channel.send_snapshot(latest_state.state)

    if latest_state.last_event_id:
        while True:
            event = await subscriber.queue.get()
            if event.id > latest_state.last_event_id:
                await channel.send_event(event.entity_id, event.state)
                break

    while True:
        event = await subscriber.queue.get()
        await channel.send_event(event.entity_id, event.state)
