import asyncio
import uuid
from dataclasses import dataclass, field

from floorcast.models import Event
from floorcast.repositories.event import EventRepository
from floorcast.services.snapshot import SnapshotService


@dataclass(kw_only=True, frozen=True)
class Client:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    queue: asyncio.Queue[Event] = field(default_factory=asyncio.Queue)


@dataclass(kw_only=True, frozen=True)
class AppState:
    clients: set[Client]
    event_repo: EventRepository
    snapshot_service: SnapshotService
