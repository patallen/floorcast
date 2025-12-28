import aiosqlite
import pytest


@pytest.fixture
async def conn():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row

    await conn.executescript("""
        CREATE TABLE events (
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
            unit TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX ix_events_domain ON events(domain);
        CREATE INDEX ix_events_entity_id ON events(entity_id);
        CREATE INDEX ix_events_timestamp ON events(timestamp);
        CREATE INDEX ix_events_type ON events(event_type);

        CREATE TABLE snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_event_id INTEGER NOT NULL REFERENCES events(id),
            state JSON NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX ix_snapshots_created_at ON snapshots(created_at);
        CREATE INDEX ix_snapshots_last_event_id ON snapshots(last_event_id);
    """)

    yield conn
    await conn.close()
