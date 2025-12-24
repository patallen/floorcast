from starlette.websockets import WebSocket

from floorcast.services.snapshot import SnapshotService


def get_snapshot_service(websocket: WebSocket) -> SnapshotService:
    return websocket.app.state.snapshot_service  # type: ignore
