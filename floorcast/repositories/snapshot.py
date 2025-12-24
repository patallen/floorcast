import json

import structlog
from aiosqlite import Connection

from floorcast.domain.models import Snapshot

logger = structlog.get_logger(__name__)


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
