from fastapi import FastAPI

from floorcast.api.routes import ws_router
from floorcast.api.state import AppState, Client
from floorcast.repositories.event import EventRepository
from floorcast.services.snapshot import SnapshotService


def create_app(
    clients: set[Client], event_repo: EventRepository, snapshot_service: SnapshotService
) -> FastAPI:
    app = FastAPI(
        name="floorcast",
    )
    app.state = AppState(
        clients=clients,
        event_repo=event_repo,
        snapshot_service=snapshot_service,
    )
    app.include_router(ws_router)
    return app
