from starlette.websockets import WebSocket

from floorcast.repositories.event import EventRepository
from floorcast.repositories.snapshot import SnapshotRepository


def get_snapshot_service(websocket: WebSocket) -> SnapshotRepository:
    return websocket.app.state.snapshot_service  # type: ignore


def get_event_repo(websocket: WebSocket) -> EventRepository:
    return websocket.app.state.event_repo  # type: ignore
