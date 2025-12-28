"""backfill units for snapshots and events

Revision ID: 003
Revises: 002
Create Date: 2025-12-28 03:21:37.688485

"""

import json
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Update all events without units
    op.execute("""
    UPDATE events
    SET unit = json_extract(data, '$.attributes.unit_of_measurement')
    WHERE unit IS NULL
    """)

    # Migrate snapshots: transform state format and add units
    conn = op.get_bind()
    snapshots = conn.execute(text("SELECT id, state FROM snapshots")).fetchall()

    # Build entity -> unit lookup from events
    units = {}
    rows = conn.execute(
        text("SELECT entity_id, unit FROM events WHERE unit IS NOT NULL GROUP BY entity_id")
    ).fetchall()
    for entity_id, unit in rows:
        units[entity_id] = unit

    for snapshot_id, state_json in snapshots:
        old_state = json.loads(state_json)
        new_state = {}
        for entity_id, value in old_state.items():
            # Unwrap nested {value: ...} or {state: ...} until we get to the actual value
            while isinstance(value, dict) and ("value" in value or "state" in value):
                value = value["value"] if "value" in value else value["state"]
            new_state[entity_id] = {"value": value, "unit": units.get(entity_id)}
        conn.execute(
            text("UPDATE snapshots SET state = :state WHERE id = :id"),
            {"state": json.dumps(new_state), "id": snapshot_id},
        )
    conn.commit()


def downgrade():
    op.execute("UPDATE events SET unit = NULL")
