from typing import TYPE_CHECKING

from fastapi import FastAPI

from floorcast.api.routes import ws_router
from floorcast.api.state import AppState

if TYPE_CHECKING:
    from floorcast.domain.models import Registry, Subscriber
    from floorcast.services.snapshot import SnapshotService


def create_app(
    subscribers: set[Subscriber],
    registry: Registry,
    snapshot_service: SnapshotService,
) -> FastAPI:
    app = FastAPI(name="floorcast")
    app.state = AppState(
        subscribers=subscribers,
        snapshot_service=snapshot_service,
        registry=registry,
    )
    app.include_router(ws_router)
    return app
