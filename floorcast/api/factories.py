from fastapi import FastAPI

from floorcast.api.routes import ws_router
from floorcast.api.state import AppState, Client
from floorcast.repositories.event import EventRepository
from floorcast.repositories.snapshot import SnapshotRepository


def create_app(
    clients: set[Client], event_repo: EventRepository, snapshot_repo: SnapshotRepository
) -> FastAPI:
    app = FastAPI(
        name="floorcast",
    )
    app.state = AppState(
        clients=clients,
        event_repo=event_repo,
        snapshot_repo=snapshot_repo,
    )
    app.include_router(ws_router)
    return app
