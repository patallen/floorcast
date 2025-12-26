import aiosqlite
import pytest

from floorcast.infrastructure.db import connect_db, init_db


@pytest.fixture
async def conn():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await init_db(conn)
    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_init_db(conn):
    await init_db(conn)

    rows = await conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [r[0] for r in await rows.fetchall()]

    assert "snapshots" in table_names
    assert "events" in table_names

    # This also includes sqlite_sequence. This assertion ensures that this test will be updated
    # when new tables are added
    assert len(table_names) == 3


@pytest.mark.asyncio
async def test_connect_db():
    async with connect_db(":memory:") as db_conn:
        assert isinstance(db_conn, aiosqlite.Connection)
        assert db_conn.row_factory == aiosqlite.Row
