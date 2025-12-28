"""add unit to event table

Revision ID: b69fddcd58aa
Revises: 0c244d37cc31
Create Date: 2025-12-28 01:28:48.264821

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE events ADD COLUMN unit TEXT;")


def downgrade() -> None:
    op.execute("ALTER TABLE events DROP COLUMN unit;")
