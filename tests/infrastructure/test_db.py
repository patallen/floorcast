import aiosqlite
import pytest

from floorcast.infrastructure.db import connect_db


@pytest.mark.asyncio
async def test_connect_db():
    async with connect_db(":memory:") as db_conn:
        assert isinstance(db_conn, aiosqlite.Connection)
        assert db_conn.row_factory == aiosqlite.Row
