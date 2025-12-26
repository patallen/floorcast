from __future__ import annotations

from fnmatch import fnmatch
from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from floorcast.domain.models import Event


class EntityBlockList:
    def __init__(self, blockers: list[str]) -> None:
        self._blockers = blockers

    def should_block(self, event: Event) -> bool:
        return any(fnmatch(event.entity_id, blocked) for blocked in self._blockers)


class FilteredEventStream:
    def __init__(self, source: AsyncIterator[Event], block_list: EntityBlockList) -> None:
        self._block_list = block_list
        self._source = source

    def __aiter__(self) -> "FilteredEventStream":
        return self

    async def __anext__(self) -> Event:
        while True:
            event = await self._source.__anext__()
            if not self._block_list.should_block(event):
                return event
