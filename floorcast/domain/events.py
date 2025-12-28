from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from floorcast.domain.models import Event, Registry


class FCEvent:
    """Base event class for all application events."""


@dataclass(kw_only=True, frozen=True)
class StateReconstructed(FCEvent):
    state: dict[str, str | None]
    last_event_id: int


@dataclass(kw_only=True, frozen=True)
class EntityStateChanged(FCEvent):
    entity_id: str
    state: str | None
    event: "Event"


@dataclass(kw_only=True, frozen=True)
class RegistryUpdated(FCEvent):
    registry: Registry
