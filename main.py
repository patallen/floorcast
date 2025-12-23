import asyncio

import structlog

from floorcast.db import connect_db, init_db
from floorcast.repository import EventRepository
from floorcast.websocket import HomeAssistantAuth, HomeAssistantWebsocket
from settings import Settings

logger = structlog.get_logger(__name__)

config = Settings()


def ha_ws_url(ha_url: str) -> str:
    return f"ws://{ha_url}/api/websocket"


async def main():
    conn = await connect_db(config.db_uri)
    await init_db(conn)

    state_cache = {}
    auth = HomeAssistantAuth(config.ha_ws_token)
    event_repo = EventRepository(conn)
    async with HomeAssistantWebsocket(ha_ws_url(config.ha_url), auth) as ws:
        async for message in ws:
            if message["type"] != "event":
                continue
            event = await event_repo.create(message)
            state_cache[event.entity_id] = event.state


if __name__ == "__main__":
    asyncio.run(main())
