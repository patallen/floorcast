from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite


@asynccontextmanager
async def connect_db(db_path: str) -> AsyncGenerator[aiosqlite.Connection]:
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()
