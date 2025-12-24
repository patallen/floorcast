from dataclasses import dataclass

from floorcast.models import Subscriber
from floorcast.repositories.event import EventRepository
from floorcast.services.snapshot import SnapshotService


@dataclass(kw_only=True, frozen=True)
class AppState:
    subscribers: set[Subscriber]
    event_repo: EventRepository
    snapshot_service: SnapshotService
