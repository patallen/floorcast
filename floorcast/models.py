import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, cast


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


@dataclass(kw_only=True)
class Event:
    id: int = -1
    entity_id: str
    event_id: uuid.UUID
    event_type: str
    external_id: str
    state: str | None
    timestamp: datetime
    data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        return cls(
            id=int(data["id"]),
            entity_id=data["entity_id"],
            event_id=uuid.UUID(data["event_id"]),
            event_type=data["event_type"],
            external_id=data["external_id"],
            state=data["state"],
            timestamp=_parse_datetime(data["timestamp"]),
            data=json.loads(data["data"]),
            metadata=json.loads(cast(str, data.get("metadata"))),
        )


@dataclass(kw_only=True)
class Snapshot:
    id: int = -1
    last_event_id: int
    state: dict[str, str | None]
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        return cls(
            id=int(data["id"]),
            last_event_id=int(data["last_event_id"]),
            state=json.loads(data["state"]),
            created_at=_parse_datetime(data["created_at"]),
        )
