import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

import aiosqlite


def adapt_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


sqlite3.register_adapter(datetime, adapt_datetime)


@asynccontextmanager
async def connect_db(db_path: str) -> AsyncGenerator[aiosqlite.Connection]:
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()
