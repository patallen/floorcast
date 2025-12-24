from collections.abc import Awaitable, Callable
from fnmatch import fnmatch
from typing import TYPE_CHECKING, AsyncIterator, Protocol, TypeVar

if TYPE_CHECKING:
    from floorcast.domain.models import Event

T = TypeVar("T", bound="HasEntityId")
RawEvent = TypeVar("RawEvent")

EventMapper = Callable[[RawEvent], Awaitable["Event"]]


class HasEntityId(Protocol):
    @property
    def entity_id(self) -> str: ...


class EntityBlockList:
    def __init__(self, blockers: list[str]) -> None:
        self._blockers = blockers

    def should_block(self, event: HasEntityId) -> bool:
        return any(fnmatch(event.entity_id, blocked) for blocked in self._blockers)


class FilteredEventStream(AsyncIterator[T]):
    def __init__(self, source: AsyncIterator[T], block_list: EntityBlockList) -> None:
        self._block_list = block_list
        self._source = source

    def __aiter__(self) -> "FilteredEventStream[T]":
        return self

    async def __anext__(self) -> T:
        while True:
            event = await self._source.__anext__()
            if not self._block_list.should_block(event):
                return event
