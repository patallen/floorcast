from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from starlette.datastructures import State

from floorcast.domain.models import Registry, Subscriber

if TYPE_CHECKING:
    from floorcast.services.snapshot import SnapshotService


@dataclass(kw_only=True, frozen=True)
class AppState(State):
    subscribers: set[Subscriber]
    registry: Registry
    snapshot_service: SnapshotService
