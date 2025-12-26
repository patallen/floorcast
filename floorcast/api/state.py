from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.datastructures import State

if TYPE_CHECKING:
    from floorcast.domain.models import Registry
    from floorcast.domain.ports import EventPublisher
    from floorcast.services.snapshot import SnapshotService


class AppState(State):
    def __init__(
        self, registry: Registry, snapshot_service: SnapshotService, event_bus: EventPublisher
    ) -> None:
        super().__init__()
        self.event_bus = event_bus
        self.registry = registry
        self.snapshot_service = snapshot_service
