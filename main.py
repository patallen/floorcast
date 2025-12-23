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
        logger.info("connected to floorcast db", db_uri=config.db_uri)
        await init_db(db_conn)

        state_cache = {}
        event_repo = EventRepository(db_conn)
        event_enricher = EventEnricher()

        async with connect(ha_ws_url(config.ha_url)) as ws:
            logger.info("connected to HA websocket", ha_url=config.ha_url)

            async with HomeAssistantProtocol(ws, config.ha_ws_token) as ha_protocol:
                await ha_protocol.subscribe("state_changed")
                logger.info("subscribed to HA events", event_types=["state_changed"])

                async for ha_event in ha_protocol:
                    event = await event_enricher.enrich(ha_event)
                    event = await event_repo.create(event)
                    logger.info(
                        "event persisted",
                        event_id=str(event.event_id),
                        entity_id=event.entity_id,
                        serial=event.id,
                        event_type=event.event_type,
                    )
                    state_cache[event.entity_id] = event.state


if __name__ == "__main__":
    try:
        logger.info("starting floorcast!")
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    logger.info("floorcast stopped :(")
