from fnmatch import fnmatch
from typing import AsyncIterator, Protocol

from floorcast.ha_protocol import HAEvent


class FilterPredicate(Protocol):
    def matches(self, event: HAEvent) -> bool: ...


class EntityIDGlobFilter:
    def __init__(self, blocklist: list[str]) -> None:
        self._blocklist = blocklist

    def matches(self, event: HAEvent) -> bool:
        return any([fnmatch(event.entity_id, blocked) for blocked in self._blocklist])


class EventPipeline:
    def __init__(
        self, filters: list[FilterPredicate], source: AsyncIterator[HAEvent]
    ) -> None:
        self._filters = filters
        self._source = source

    def __aiter__(self) -> "EventPipeline":
        return self

    def any_match(self, event: HAEvent) -> bool:
        for predicate in self._filters:
            if predicate.matches(event):
                return True
        return False

    async def __anext__(self) -> HAEvent:
        while True:
            event = await self._source.__anext__()
            if not self.any_match(event):
                return event
