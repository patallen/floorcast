import asyncio
from typing import TYPE_CHECKING

import structlog
import uvicorn
from fastapi import FastAPI

from floorcast.adapters.home_assistant import connect_home_assistant, map_ha_event
from floorcast.api.factories import create_app
from floorcast.domain.filtering import EntityBlockList
from floorcast.infrastructure.config import Config
from floorcast.infrastructure.db import connect_db, init_db
from floorcast.infrastructure.logging import configure_logging
from floorcast.ingest import run_ingestion
from floorcast.repositories.event import EventRepository
from floorcast.repositories.snapshot import SnapshotRepository
from floorcast.services.snapshot import SnapshotService

if TYPE_CHECKING:
    from floorcast.domain.models import Subscriber

config = Config()  # type: ignore[call-arg]
configure_logging(config.log_level, config.log_to_console)
logger = structlog.get_logger(__name__)


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

        subscribers: set[Subscriber] = set()
        event_repo = EventRepository(db_conn)
        snapshot_repo = SnapshotRepository(db_conn)
        snapshot_service = SnapshotService(
            snapshot_repo, event_repo, config.snapshot_interval_seconds
        )

        app = create_app(subscribers, event_repo, snapshot_service)

        block_list = EntityBlockList(config.entity_blocklist)
        event_source = connect_home_assistant(
            config.ha_websocket_url, config.ha_websocket_token
        )
        event_mapper = map_ha_event

        ingest_coroutine = run_ingestion(
            subscribers,
            event_repo,
            snapshot_service,
            block_list,
            event_source,
            event_mapper,
        )
        websocket_coroutine = run_websocket_server(app)
        await asyncio.gather(ingest_coroutine, websocket_coroutine)


if __name__ == "__main__":
    try:
        logger.info("starting floorcast!")
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    logger.info("floorcast stopped :(")
