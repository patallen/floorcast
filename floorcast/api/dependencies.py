from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request, WebSocket

if TYPE_CHECKING:
    from floorcast.domain.events import FCEvent
    from floorcast.domain.ports import (
        EventPublisher,
        EventStore,
        StateReconstructor,
        WebsocketManager,
    )


def get_event_repo(request: Request) -> EventStore:
    return request.app.state.event_repo  # type: ignore


def get_state_service(request: Request) -> StateReconstructor:
    return request.app.state.state_service  # type: ignore


def get_state_service_ws(websocket: WebSocket) -> StateReconstructor:
    return websocket.app.state.state_service  # type: ignore


# WebSocket versions for backward compatibility
def get_event_bus_ws(websocket: WebSocket) -> "EventPublisher[FCEvent]":
    return websocket.app.state.event_bus  # type: ignore


def get_websocket_service_ws(websocket: WebSocket) -> "WebsocketManager":
    return websocket.app.state.websocket_service  # type: ignore
