import json
import uuid
from datetime import datetime
from typing import Any

from aiosqlite import Connection
from structlog import get_logger

from floorcast.models import Event

logger = get_logger(__name__)


def map_event(message: dict[str, Any]) -> Event:
    event = message["event"]
    event_type = event["event_type"]
    data = event["data"]
    entity_id = data["entity_id"]
    new_state = data["new_state"]
    state = new_state["state"]
    external_id = event["context"]["id"]
    timestamp = datetime.fromisoformat(event["time_fired"])

    return Event(
        id=None,
        external_id=external_id,
        entity_id=entity_id,
        event_id=uuid.uuid4(),
        state=state,
        event_type=event_type,
        timestamp=timestamp,
        data=new_state,
    )


class EventRepository:
    def __init__(self, conn: Connection):
        self.conn = conn

    async def create(self, data: dict[str, Any]) -> Event:
        event = map_event(data)
        row = await self.conn.execute_insert(
            """
            INSERT INTO events (
                event_id, event_type, external_id, entity_id, timestamp, state, data
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(event.event_id),
                event.event_type,
                event.external_id,
                event.entity_id,
                event.timestamp,
                event.state,
                json.dumps(event.data),
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
        row = cursor.fetchone()
        return Event(**row) if row else None
