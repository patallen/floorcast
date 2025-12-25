from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state = AppState(
        subscribers=subscribers,
        snapshot_service=snapshot_service,
        registry=registry,
    )
    app.include_router(ws_router)
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
    return app
