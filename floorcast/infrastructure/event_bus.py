import asyncio
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class EventBus(Generic[T]):
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[T]] = set()

    def publish(self, event: T) -> None:
        for queue in self._subscribers:
            queue.put_nowait(event)

    def subscribe(self, queue: asyncio.Queue[T]) -> Callable[[], None]:
        self._subscribers.add(queue)

        def unsubscribe() -> None:
            self._subscribers.discard(queue)

        return unsubscribe
