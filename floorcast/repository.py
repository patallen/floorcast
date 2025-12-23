import json

from aiosqlite import Connection
from structlog import get_logger

from floorcast.models import Event

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
                json.dumps(event.data),
                json.dumps(event.metadata or {}),
            ),
        )
        (event.id,) = row
        await self.conn.commit()
        logger.info(
            "successfully inserted event",
            serial=event.id,
            external_id=event.external_id,
            event_type=event.event_type,
        )
        return event

    async def get_by_serial(self, serial: int) -> Event | None:
        cursor = await self.conn.execute("SELECT * FROM events WHERE id = ?", (serial,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return Event.from_dict(dict(row))
