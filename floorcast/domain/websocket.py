import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WSMessage:
    type: str
    data: dict[str, Any] | str | None = None


@dataclass(frozen=True)
class WSConnection:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    queue: asyncio.Queue[WSMessage] = field(default_factory=asyncio.Queue)
    __subscriptions: set[str] = field(default_factory=set)

    @property
    def subscriptions(self) -> tuple[str, ...]:
        return tuple(self.__subscriptions)

    def subscribe(self, subscription: str) -> None:
        self.__subscriptions.add(subscription)

    def unsubscribe(self, subscription: str) -> None:
        self.__subscriptions.discard(subscription)

    def __hash__(self) -> int:
        return hash(self.id)
