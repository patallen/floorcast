from __future__ import annotations

import asyncio

import structlog
from websockets import ConnectionClosed

from floorcast.adapters.home_assistant import connect_home_assistant
from floorcast.api.factories import create_app
from floorcast.api.state import AppState
from floorcast.domain.filtering import EntityBlockList
from floorcast.domain.models import Event, Registry
from floorcast.infrastructure.config import Config
from floorcast.infrastructure.db import connect_db, init_db
from floorcast.infrastructure.event_bus import EventBus
from floorcast.infrastructure.logging import configure_logging
from floorcast.ingest import run_ingestion
from floorcast.repositories.event import EventRepository
from floorcast.repositories.snapshot import SnapshotRepository
from floorcast.server import run_websocket_server
from floorcast.services.snapshot import SnapshotService

config = Config()  # type: ignore[call-arg]
configure_logging(config.log_level, config.log_to_console)
logger = structlog.get_logger(__name__)


async def main() -> None:
    event_bus = EventBus[Event]()

    async with connect_db(config.db_uri) as db_conn:
        logger.info("connected to floorcast db", db_uri=config.db_uri)
        await init_db(db_conn)

        event_repo = EventRepository(db_conn)
        snapshot_repo = SnapshotRepository(db_conn)
        snapshot_service = SnapshotService(
            snapshot_repo, event_repo, config.snapshot_interval_seconds
        )

        blocklist = EntityBlockList(config.entity_blocklist)

        app_state = AppState(
            registry=Registry.empty(), snapshot_service=snapshot_service, event_bus=event_bus
        )
        app = create_app(app_state)

        async def ingestion_loop() -> None:
            backoff = 2
            while True:
                try:
                    async with connect_home_assistant(
                        config.ha_websocket_url, config.ha_websocket_token
                    ) as client:
                        backoff = 2
                        app_state.registry = await client.fetch_registry()
                        await run_ingestion(
                            event_bus=event_bus,
                            event_source=client,
                            snapshot_service=app_state.snapshot_service,
                            event_repo=event_repo,
                            entity_blocklist=blocklist,
                        )
                except (ConnectionClosed, ConnectionRefusedError, OSError):
                    logger.warning("connection to home assistant lost", retry_in=backoff)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)

        server_fn = run_websocket_server(app)
        await asyncio.gather(ingestion_loop(), server_fn)


if __name__ == "__main__":
    try:
        logger.info("starting floorcast!")
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    logger.info("floorcast stopped :(")
