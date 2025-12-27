import json
from datetime import datetime

import structlog
from aiosqlite import Connection

from floorcast.domain.models import Snapshot
from floorcast.domain.ports import SnapshotStore

logger = structlog.get_logger(__name__)


class SnapshotRepository(SnapshotStore):
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

        snapshot.id = row[0]  # type: ignore[index]
        await self.conn.commit()
        updated = await self.get_by_id(snapshot.id)
        snapshot.created_at = updated.created_at
        return snapshot

    async def get_by_id(self, snapshot_id: int) -> Snapshot:
        cursor = await self.conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,))
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Snapshot with id {snapshot_id} not found")
        return Snapshot.from_dict(dict(row))

    async def get_before_timestamp(self, timestamp: datetime) -> Snapshot | None:
        cursor = await self.conn.execute(
            """
            SELECT * FROM snapshots
            WHERE datetime(created_at) < datetime(?)
            ORDER BY id DESC LIMIT 1
            """,
            (timestamp.isoformat(),),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return Snapshot.from_dict(dict(row))

    async def get_latest(self) -> Snapshot | None:
        cursor = await self.conn.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1")
        row = await cursor.fetchone()
        if not row:
            return None
        return Snapshot.from_dict(dict(row))
