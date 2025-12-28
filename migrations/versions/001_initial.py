"""Initial migration

Revision ID: 0c244d37cc31
Revises:
Create Date: 2025-12-28 01:13:23.796547

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_events_domain ON events(domain)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_events_entity_id ON events(entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_events_timestamp ON events(timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_events_type ON events(event_type)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        last_event_id INTEGER NOT NULL REFERENCES events(id),
        state JSON NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    op.execute("CREATE INDEX IF NOT EXISTS ix_snapshots_created_at ON snapshots(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_snapshots_last_event_id ON snapshots(last_event_id)")


def downgrade() -> None:
    op.execute("DROP TABLE snapshots")
    op.execute("DROP TABLE events")
