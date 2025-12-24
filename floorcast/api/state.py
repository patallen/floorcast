from dataclasses import dataclass
from typing import TYPE_CHECKING

from floorcast.domain.models import Subscriber

if TYPE_CHECKING:
    from floorcast.services.snapshot import SnapshotService


@dataclass(kw_only=True, frozen=True)
class AppState:
    subscribers: set[Subscriber]
    snapshot_service: SnapshotService
