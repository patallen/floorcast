import json
from datetime import datetime

import structlog
from aiosqlite import Connection

from floorcast.domain.models import CompactEvent, Event
from floorcast.domain.ports import EventStore

logger = structlog.get_logger(__name__)


class EventRepository(EventStore):
    def __init__(self, conn: Connection):
        self.conn = conn

    async def create(self, event: Event) -> Event:
        cursor = await self.conn.execute(
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
                metadata,
                unit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(external_id) DO UPDATE SET external_id=excluded.external_id
            RETURNING *
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
                event.unit,
            ),
        )
        row = await cursor.fetchone()
        event.id = row[0]  # type: ignore[index]
        await self.conn.commit()
        return event

    async def get_timeline_between(self, start_id: int, end_time: datetime) -> list[CompactEvent]:
        rows = await self.conn.execute_fetchall(
            """
            SELECT id, entity_id, timestamp, state, unit FROM events
            WHERE id > ? AND timestamp < ?
            ORDER BY timestamp, id
            """,
            (start_id, end_time),
        )
        events = [
            CompactEvent(
                id=row[0],
                entity_id=row[1],
                timestamp=int(datetime.fromisoformat(row[2]).timestamp() * 1000),
                state=row[3],
                unit=row[4],
            )
            for row in rows
        ]
        logger.debug(
            "fetched events for timeline",
            after_id=start_id,
            before_timestamp=end_time.isoformat(),
            count=len(events),
        )
        return events

    async def get_by_id(self, serial: int) -> Event | None:
        cursor = await self.conn.execute("SELECT * FROM events WHERE id = ?", (serial,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return Event.from_dict(dict(row))

    async def get_between_id_and_timestamp(self, id: int, timestamp: datetime) -> list[Event]:
        rows = await self.conn.execute_fetchall(
            "SELECT * FROM events WHERE id > ? AND timestamp < ?",
            (id, timestamp),
        )
        events = [Event.from_dict(dict(row)) for row in rows]
        logger.debug(
            "fetched events", after_id=id, before_timestamp=timestamp.isoformat(), count=len(events)
        )
        return events
