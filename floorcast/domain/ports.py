from datetime import datetime
from typing import Protocol

from floorcast.domain.models import Event, Snapshot


class SnapshotStore(Protocol):
    async def create(self, snapshot: Snapshot) -> Snapshot: ...
    async def get_latest(self) -> Snapshot | None: ...
    async def get_before_timestamp(self, timestamp: datetime) -> Snapshot | None: ...


class EventStore(Protocol):
    async def create(self, event: Event) -> Event: ...
    async def get_between_id_and_timestamp(
        self, event_id: int, timestamp: datetime
    ) -> list[Event]: ...
