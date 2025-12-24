import json
from datetime import datetime

import structlog
from aiosqlite import Connection

from floorcast.models import Event

logger = structlog.get_logger(__name__)


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
                domain,
                entity_id,
                timestamp,
                state,
                data,
                metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (external_id) DO NOTHING
            """,
            (
                str(event.event_id),
                event.event_type,
                event.external_id,
                event.domain,
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
