from typing import TYPE_CHECKING

from fastapi import Request, WebSocket

if TYPE_CHECKING:
    from floorcast.domain.ports import EventPublisher
    from floorcast.repositories.event import EventRepository
    from floorcast.services.snapshot import SnapshotService


def get_snapshot_service(request: Request) -> "SnapshotService":
    return request.app.state.snapshot_service  # type: ignore


def get_event_repo(request: Request) -> "EventRepository":
    return request.app.state.snapshot_service.event_repo  # type: ignore


# WebSocket versions for backward compatibility
def get_snapshot_service_ws(websocket: WebSocket) -> "SnapshotService":
    return websocket.app.state.snapshot_service  # type: ignore


def get_event_bus_ws(websocket: WebSocket) -> "EventPublisher":
    return websocket.app.state.event_bus  # type: ignore
