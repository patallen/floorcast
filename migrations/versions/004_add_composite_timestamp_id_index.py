"""add composite timestamp_id index

Revision ID: 582c563190ab
Revises: 003
Create Date: 2026-01-14 23:12:38.084744

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, Sequence[str], None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE INDEX ix_events_timestamp_id ON events(timestamp, id);")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX ix_events_timestamp_id;")
