import os
import tempfile
from pathlib import Path

import aiosqlite
import pytest
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
async def conn():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(alembic_cfg, "head")

    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    yield conn
    await conn.close()
    os.unlink(db_path)
