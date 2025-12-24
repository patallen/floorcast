from typing import TYPE_CHECKING

from fastapi import FastAPI

from floorcast.api.routes import ws_router
from floorcast.api.state import AppState

if TYPE_CHECKING:
    from floorcast.domain.models import Subscriber
    from floorcast.repositories.event import EventRepository
    from floorcast.services.snapshot import SnapshotService


def create_app(
    subscribers: set[Subscriber],
    event_repo: EventRepository,
    snapshot_service: SnapshotService,
) -> FastAPI:
    app = FastAPI(name="floorcast")
    app.state = AppState(
        subscribers=subscribers,
        event_repo=event_repo,
        snapshot_service=snapshot_service,
    )
    app.include_router(ws_router)
    return app
