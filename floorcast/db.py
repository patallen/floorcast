from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite


@asynccontextmanager
async def connect_db(db_path: str) -> AsyncGenerator[aiosqlite.Connection]:
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


async def init_db(conn: aiosqlite.Connection) -> None:
    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT,
            domain TEXT NOT NULL,
            external_id TEXT UNIQUE NOT NULL,
            event_id TEXT UNIQUE NOT NULL,
            event_type TEXT NOT NULL,
            entity_id TEXT,
            timestamp DATETIME NOT NULL,
            data JSON NOT NULL DEFAULT '{}',
            metadata JSON NOT NULL DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS ix_events_domain ON events(domain);
        CREATE INDEX IF NOT EXISTS ix_events_entity_id ON events(entity_id);
        CREATE INDEX IF NOT EXISTS ix_events_timestamp ON events(timestamp);
        CREATE INDEX IF NOT EXISTS ix_events_type ON events(event_type);

        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_event_id INTEGER NOT NULL REFERENCES events(id),
            state JSON NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS ix_snapshots_created_at ON snapshots(created_at);
        CREATE INDEX IF NOT EXISTS (
            ix_snapshots_last_event_id ON snapshots(last_event_id)
        );
        """
    )
