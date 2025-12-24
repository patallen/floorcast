from dataclasses import dataclass
from typing import TYPE_CHECKING

from floorcast.domain.models import Subscriber

if TYPE_CHECKING:
    from floorcast.repositories.event import EventRepository
    from floorcast.services.snapshot import SnapshotService


@dataclass(kw_only=True, frozen=True)
class AppState:
    subscribers: set[Subscriber]
    event_repo: EventRepository
    snapshot_service: SnapshotService
