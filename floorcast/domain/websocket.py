import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any


# TODO: websocket message should be a discriminated union
#  RegistryResponse, SnapshotResponse, EntityStateUpdated, Pong
@dataclass(frozen=True)
class WSMessage:
    type: str
    data: dict[str, Any] | str | None = None


@dataclass(frozen=True)
class WSConnection:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    queue: asyncio.Queue[WSMessage] = field(default_factory=asyncio.Queue)

    def __hash__(self) -> int:
        return hash(self.id)
