from __future__ import annotations

from typing_extensions import TYPE_CHECKING

from floorcast.domain.events import FCEvent, RegistryUpdated
from floorcast.domain.models import Registry

if TYPE_CHECKING:
    from floorcast.domain.ports import EventPublisher


class RegistryService:
    def __init__(self, bus: EventPublisher[FCEvent]) -> None:
        self._registry = Registry.empty()
        self._bus = bus
        self._unsubscribe = bus.subscribe(RegistryUpdated, self._handle_registry_updated_event)

    def get_registry(self) -> Registry:
        return self._registry

    async def _handle_registry_updated_event(self, event: RegistryUpdated) -> None:
        self._registry = event.registry
