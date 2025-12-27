from __future__ import annotations

import asyncio

import structlog
from websockets import ConnectionClosed

from floorcast.adapters.home_assistant import connect_home_assistant
from floorcast.api.app_state import AppState
from floorcast.api.factories import create_app
from floorcast.domain.event_filtering import EntityBlockList
from floorcast.domain.models import Event, Registry
from floorcast.domain.snapshot_policies import ElapsedTimePolicy
from floorcast.infrastructure.backoff import Backoff
from floorcast.infrastructure.config import Config
from floorcast.infrastructure.db import connect_db, init_db
from floorcast.infrastructure.event_bus import EventBus
from floorcast.infrastructure.logging import configure_logging
from floorcast.repositories.event import EventRepository
from floorcast.repositories.snapshot import SnapshotRepository
from floorcast.server import run_websocket_server
from floorcast.services.ingestion import IngestionService
from floorcast.services.state import StateService

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
        state_service = StateService(snapshot_repo, event_repo)
        blocklist = EntityBlockList(config.entity_blocklist)

        app_state = AppState(
            registry=Registry.empty(),
            event_bus=event_bus,
            event_repo=event_repo,
            state_service=state_service,
        )
        app = create_app(app_state)

        snapshot_policy = ElapsedTimePolicy(config.snapshot_interval_seconds)
        ingest_service = IngestionService(
            event_bus=event_bus,
            event_repo=event_repo,
            snapshot_repo=snapshot_repo,
            state_service=state_service,
            entity_blocklist=blocklist,
            snapshot_policy=snapshot_policy,
        )
        websocket_url = config.ha_websocket_url
        websocket_token = config.ha_websocket_token

        async def ingestion_loop() -> None:
            for backoff in Backoff(2, 60):
                try:
                    async with connect_home_assistant(websocket_url, websocket_token) as client:
                        logger.info("connection to home assistant", websocket_url=websocket_url)
                        app_state.registry = await client.fetch_registry()
                        await ingest_service.run(client)
                        backoff.reset()
                except (ConnectionClosed, ConnectionRefusedError, OSError):
                    logger.warning("connection to home assistant lost", retry_in=backoff)
                    await asyncio.sleep(backoff.wait_seconds())

        server_fn = run_websocket_server(app)
        await asyncio.gather(ingestion_loop(), server_fn)


if __name__ == "__main__":
    try:
        logger.info("starting floorcast!")
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    logger.info("floorcast stopped :(")
