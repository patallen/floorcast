import asyncio
from typing import Callable, Generic, TypeVar

import structlog

T = TypeVar("T")

logger = structlog.get_logger(__name__)


class EventBus(Generic[T]):
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[T]] = set()

    def publish(self, event: T) -> None:
        for queue in self._subscribers:
            queue.put_nowait(event)

    def subscribe(self, queue: asyncio.Queue[T]) -> Callable[[], None]:
        self._subscribers.add(queue)
        logger.debug(
            "subscriber added", queue_id=id(queue), total_subscribers=len(self._subscribers)
        )

        def unsubscribe() -> None:
            self._subscribers.discard(queue)
            logger.debug(
                "subscriber removed", queue_id=id(queue), total_subscribers=len(self._subscribers)
            )

        return unsubscribe
