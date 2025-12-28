from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.datastructures import State

from floorcast.domain.events import FCEvent

if TYPE_CHECKING:
    from floorcast.domain.models import Registry
    from floorcast.domain.ports import EventPublisher, EventStore, StateReconstructor


class AppState(State):
    def __init__(
        self,
        registry: Registry,
        event_bus: EventPublisher[FCEvent],
        event_repo: EventStore,
        state_service: StateReconstructor,
    ) -> None:
        super().__init__()
        self.event_repo = event_repo
        self.event_bus = event_bus
        self.registry = registry
        self.state_service = state_service
