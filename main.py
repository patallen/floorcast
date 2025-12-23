import asyncio

import structlog
from websockets import connect

from floorcast.db import connect_db, init_db
from floorcast.enrichment import EventEnricher
from floorcast.protocol import HomeAssistantProtocol
from floorcast.repository import EventRepository
from settings import Settings

logger = structlog.get_logger(__name__)

config = Settings()


def ha_ws_url(ha_url: str) -> str:
    return f"ws://{ha_url}/api/websocket"


async def main():
    async with connect_db(config.db_uri) as db_conn:
        await init_db(db_conn)

        state_cache = {}
        event_repo = EventRepository(db_conn)
        event_enricher = EventEnricher()

        async with connect(ha_ws_url(config.ha_url)) as ws:
            async with HomeAssistantProtocol(ws, config.ha_ws_token) as ha_protocol:
                await ha_protocol.subscribe("state_changed")
                async for ha_event in ha_protocol:
                    event = await event_enricher.enrich(ha_event)
                    event = await event_repo.create(event)
                    state_cache[event.entity_id] = event.state


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
