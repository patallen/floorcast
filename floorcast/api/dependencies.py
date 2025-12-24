from typing import TYPE_CHECKING

from starlette.websockets import WebSocket

if TYPE_CHECKING:
    from floorcast.services.snapshot import SnapshotService


def get_snapshot_service(websocket: WebSocket) -> "SnapshotService":
    return websocket.app.state.snapshot_service  # type: ignore
