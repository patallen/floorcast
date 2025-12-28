from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.datastructures import State

from floorcast.domain.events import FCEvent

if TYPE_CHECKING:
    from floorcast.domain.ports import EventPublisher, EventStore
    from floorcast.services.registry import RegistryService
    from floorcast.services.state import StateService
    from floorcast.services.websocket import WebsocketService


class AppState(State):
    def __init__(
        self,
        registry_service: RegistryService,
        event_bus: EventPublisher[FCEvent],
        event_repo: EventStore,
        state_service: StateService,
        websocket_service: WebsocketService,
    ) -> None:
        super().__init__()
        self.event_repo = event_repo
        self.event_bus = event_bus
        self.registry_service = registry_service
        self.state_service = state_service
        self.websocket_service = websocket_service
