from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from floorcast.api.routes import ws_router

if TYPE_CHECKING:
    from floorcast.api.app_state import AppState


def create_app(app_state: AppState) -> FastAPI:
    app = FastAPI(name="floorcast")
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state = app_state
    app.include_router(ws_router)
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
    return app
