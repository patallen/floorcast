import json
from datetime import datetime

from aiosqlite import Connection
from structlog import get_logger

from floorcast.models import Event, Snapshot

logger = get_logger(__name__)


class EventRepository:
    def __init__(self, conn: Connection):
        self.conn = conn

    async def create(self, event: Event) -> Event:
        row = await self.conn.execute_insert(
            """
            INSERT INTO events (
                event_id,
                event_type,
                external_id,
                entity_id,
                timestamp,
                state,
                data,
                metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(event.event_id),
                event.event_type,
                event.external_id,
                event.entity_id,
                event.timestamp,
                event.state,
                json.dumps(event.data or {}),
                json.dumps(event.metadata or {}),
            ),
        )
        if not row:
            raise ValueError("Failed to create event")
        event.id = row[0]
        await self.conn.commit()
        return event

    async def get_by_serial(self, serial: int) -> Event | None:
        cursor = await self.conn.execute("SELECT * FROM events WHERE id = ?", (serial,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return Event.from_dict(dict(row))

    async def get_between_id_and_timestamp(
        self, id: int, timestamp: datetime
    ) -> list[Event]:
        rows = await self.conn.execute_fetchall(
            "SELECT * FROM events WHERE id > ? AND timestamp < ?",
            (id, timestamp.isoformat()),
        )
        return [Event.from_dict(dict(row)) for row in rows]


class SnapshotRepository:
    def __init__(self, conn: Connection):
        self.conn = conn

    async def create(self, snapshot: Snapshot) -> Snapshot:
        row = await self.conn.execute_insert(
            "INSERT INTO snapshots (last_event_id, state) VALUES (?, ?)",
            (
                snapshot.last_event_id,
                json.dumps(snapshot.state),
            ),
        )
        if not row:
            raise ValueError("Failed to create snapshot")
        (snapshot.id,) = row
        await self.conn.commit()
        updated = await self.get_by_id(snapshot.id)
        snapshot.created_at = updated.created_at
        return snapshot

    async def get_by_id(self, snapshot_id: int) -> Snapshot:
        cursor = await self.conn.execute(
            "SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Snapshot with id {snapshot_id} not found")
        return Snapshot.from_dict(dict(row))

    async def get_latest(self) -> Snapshot | None:
        cursor = await self.conn.execute(
            "SELECT * FROM snapshots ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return Snapshot.from_dict(dict(row))
