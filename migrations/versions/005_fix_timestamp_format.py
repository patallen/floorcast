"""fix timestamp format

Revision ID: 005
Revises: 004
Create Date: 2026-01-16

"""

from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, Sequence[str], None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE events SET timestamp = REPLACE(REPLACE(timestamp, 'T', ' '), '+00:00', '');")


def downgrade() -> None:
    # Can't reliably restore the original format
    pass
