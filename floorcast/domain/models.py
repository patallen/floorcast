import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, cast


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


@dataclass(kw_only=True, frozen=True, slots=True)
class CompactEvent:
    id: int
    entity_id: str
    timestamp: int  # Unix timestamp in milliseconds
    state: str | None
    unit: str | None


@dataclass(kw_only=True)
class Event:
    id: int = -1
    domain: str
    entity_id: str
    event_id: uuid.UUID
    event_type: str
    external_id: str
    state: str | None
    timestamp: datetime
    data: dict[str, Any]
    unit: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        return cls(
            id=int(data["id"]),
            entity_id=data["entity_id"],
            domain=data["domain"],
            event_id=uuid.UUID(data["event_id"]),
            event_type=data["event_type"],
            external_id=data["external_id"],
            state=data["state"],
            timestamp=_parse_datetime(data["timestamp"]),
            data=json.loads(data["data"]),
            unit=data["unit"],
            metadata=json.loads(cast(str, data.get("metadata") or "{}")),
        )


@dataclass(kw_only=True)
class Snapshot:
    id: int = -1
    last_event_id: int
    state: dict[str, Any]
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        return cls(
            id=int(data["id"]),
            last_event_id=int(data["last_event_id"]),
            state=json.loads(data["state"]),
            created_at=_parse_datetime(data["created_at"]),
        )


@dataclass(kw_only=True)
class Area:
    id: str
    display_name: str
    floor_id: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Area":
        return cls(
            id=data["area_id"],
            display_name=data["name"],
            floor_id=data["floor_id"],
        )


@dataclass(kw_only=True)
class Entity:
    id: str
    device_id: str
    domain: str
    display_name: str
    area_id: str | None
    entity_category: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        entity_id = data["entity_id"]
        return cls(
            id=data["entity_id"],
            domain=entity_id.split(".")[0],
            display_name=data.get("name") or data.get("original_name") or entity_id,
            area_id=data["area_id"],
            device_id=data["device_id"],
            entity_category=data.get("entity_category"),
        )


@dataclass(kw_only=True)
class Device:
    id: str
    area_id: str | None
    display_name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Device":
        return cls(
            id=data["id"],
            area_id=data["area_id"],
            display_name=data.get("name_by_user") or data["name"],
        )


@dataclass(kw_only=True)
class Floor:
    id: str
    display_name: str
    level: int | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Floor":
        return cls(
            id=data["floor_id"],
            display_name=data["name"],
            level=data.get("level"),
        )


@dataclass(kw_only=True, frozen=True)
class Registry:
    entities: dict[str, Entity]
    devices: dict[str, Device]
    areas: dict[str, Area]
    floors: dict[str, Floor]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entities": {e.id: asdict(e) for e in self.entities.values()},
            "devices": {d.id: asdict(d) for d in self.devices.values()},
            "areas": {a.id: asdict(a) for a in self.areas.values()},
            "floors": {f.id: asdict(f) for f in self.floors.values()},
        }

    @classmethod
    def empty(cls) -> "Registry":
        return cls(entities={}, devices={}, areas={}, floors={})


@dataclass(kw_only=True, frozen=True)
class ConstructedState:
    state: dict[str, Any]
    last_event_id: int | None
    snapshot_id: int | None
    snapshot_time: datetime | None
