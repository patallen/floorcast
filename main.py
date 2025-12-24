import asyncio

import structlog
import uvicorn
from fastapi import FastAPI
from websockets import connect

from floorcast.api.factories import create_app
from floorcast.api.state import Client
from floorcast.config import Config
from floorcast.db import connect_db, init_db
from floorcast.event_pipeline import EntityIDGlobFilter, EventPipeline
from floorcast.ha_protocol import HomeAssistantProtocol
from floorcast.logging import configure_logging
from floorcast.repositories.event import EventRepository
from floorcast.repositories.snapshot import SnapshotRepository
from floorcast.services.enrichment import EnrichmentService
from floorcast.services.snapshot import SnapshotService

config = Config()  # type: ignore[call-arg]
configure_logging(config.log_level, config.log_to_console)
logger = structlog.get_logger(__name__)


async def run_ingestion(
    clients: set[Client], event_repo: EventRepository, snapshot_repo: SnapshotRepository
) -> None:
    entity_filters = EntityIDGlobFilter(config.entity_blocklist)
    event_enricher = EnrichmentService()
    snapshot_service = SnapshotService(
        snapshot_repo, event_repo, config.snapshot_interval_seconds
    )
    await snapshot_service.initialize()
    logger.info("snapshot service initialized")

    async with connect(config.ha_websocket_url) as ws:
        logger.info("connected to HA websocket", ha_url=config.ha_websocket_url)

        async with HomeAssistantProtocol(ws, config.ha_websocket_token) as ha_protocol:
            await ha_protocol.subscribe("state_changed")
            logger.info("subscribed to HA events", event_types=["state_changed"])

            event_pipeline = EventPipeline([entity_filters], ha_protocol)
            async for ha_event in event_pipeline:
                event = await event_enricher.enrich(ha_event)
                event = await event_repo.create(event)
                logger.info(
                    "event persisted",
                    event_id=str(event.event_id),
                    entity_id=event.entity_id,
                    serial=event.id,
                    event_type=event.event_type,
                )
                snapshot_service.update_state(event.entity_id, event.state)
                for client in clients:
                    client.queue.put_nowait(event)
                if snapshot := await snapshot_service.maybe_snapshot(event.id):
                    logger.info(
                        "snapshot taken",
                        snapshot_id=snapshot.id,
                        last_event_id=snapshot.last_event_id,
                    )


async def run_websocket_server(app: FastAPI) -> None:
    server_config = uvicorn.Config(
        app, host="0.0.0.0", port=8000, log_level="warning", access_log=False
    )
    server = uvicorn.Server(server_config)
    await server.serve()


async def main() -> None:
    async with connect_db(config.db_uri) as db_conn:
        logger.info("connected to floorcast db", db_uri=config.db_uri)
        await init_db(db_conn)

        clients: set[Client] = set()
        event_repo = EventRepository(db_conn)
        snapshot_repo = SnapshotRepository(db_conn)

        app = create_app(clients, event_repo, snapshot_repo)

        ingest_coroutine = run_ingestion(clients, event_repo, snapshot_repo)
        websocket_coroutine = run_websocket_server(app)
        await asyncio.gather(ingest_coroutine, websocket_coroutine)


if __name__ == "__main__":
    try:
        logger.info("starting floorcast!")
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    logger.info("floorcast stopped :(")
