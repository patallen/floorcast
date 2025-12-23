import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(kw_only=True)
class Event:
    id: int | None = None
    entity_id: str
    event_id: uuid.UUID
    event_type: str
    external_id: str
    state: str
    timestamp: datetime
    data: dict[str, Any]
    metadata: dict[str, Any] | None = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        return cls(
            id=int(data["id"]),
            entity_id=data["entity_id"],
            event_id=uuid.UUID(data["event_id"]),
            event_type=data["event_type"],
            external_id=data["external_id"],
            state=data["state"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            data=data["data"],
            metadata=data.get("metadata"),
        )
