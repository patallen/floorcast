from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.datastructures import State

if TYPE_CHECKING:
    from floorcast.domain.models import Registry, Subscriber
    from floorcast.services.snapshot import SnapshotService


class AppState(State):
    def __init__(
        self,
        registry: Registry,
        snapshot_service: SnapshotService,
        subscribers: set[Subscriber] | None = None,
    ) -> None:
        super().__init__()
        self.subscribers: set[Subscriber] = subscribers or set()
        self.registry = registry
        self.snapshot_service = snapshot_service
