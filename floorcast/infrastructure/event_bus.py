import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine, Generic, TypeVar

import structlog

from floorcast.common.aio import create_logged_task

logger = structlog.get_logger(__name__)


T = TypeVar("T")


class TypedEventBus(Generic[T]):
    def __init__(self) -> None:
        self._registry: dict[type, set[Callable[..., Coroutine[Any, Any, None]]]] = defaultdict(set)
        self._pending_tasks: set[asyncio.Task[Any]] = set()

    def subscribe[T](
        self, event_type: type[T], callback: Callable[[T], Coroutine[Any, Any, None]]
    ) -> Callable[[], None]:
        self._registry[event_type].add(callback)

        def unsubscribe() -> None:
            self._registry[event_type].discard(callback)

        return unsubscribe

    def publish(self, event: T) -> None:
        for callback in self._registry[type(event)]:
            task = create_logged_task(callback(event))
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

    async def wait_all(self) -> None:
        await asyncio.gather(*self._pending_tasks)
