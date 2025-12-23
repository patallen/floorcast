from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite


@asynccontextmanager
async def connect_db(db_path: str) -> AsyncGenerator[aiosqlite.Connection]:
    conn = await aiosqlite.connect(db_path)
    try:
        yield conn
    finally:
        await conn.close()


async def init_db(conn: aiosqlite.Connection) -> None:
    await conn.executescript(
        """
        DROP TABLE IF EXISTS events; 
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT,
            external_id TEXT UNIQUE NOT NULL,
            event_id TEXT UNIQUE NOT NULL,
            event_type TEXT NOT NULL,
            entity_id TEXT,
            timestamp DATETIME NOT NULL,
            data JSON NOT NULL,
            metadata JSON NOT NULL DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS ix_events_timestamp ON events(timestamp);
        CREATE INDEX IF NOT EXISTS ix_events_entity_id ON events(entity_id);
        CREATE INDEX IF NOT EXISTS ix_events_type ON events(event_type);

        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            state JSON NOT NULL
        );

        CREATE INDEX IF NOT EXISTS ix_snapshots_timestamp ON snapshots(timestamp);
        """
    )
