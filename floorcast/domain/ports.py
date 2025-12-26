from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from floorcast.domain.models import Event, Snapshot


class SnapshotStore(Protocol):
    async def create(self, snapshot: Snapshot) -> Snapshot: ...
    async def get_latest(self) -> Snapshot | None: ...
    async def get_before_timestamp(self, timestamp: datetime) -> Snapshot | None: ...


class EventStore(Protocol):
    async def create(self, event: Event) -> Event: ...
    async def get_by_id(self, event_id: int) -> Event | None: ...
    async def get_between_id_and_timestamp(
        self, event_id: int, timestamp: datetime
    ) -> list[Event]: ...
