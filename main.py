from __future__ import annotations

import asyncio

import structlog
from websockets import ConnectionClosed

from floorcast.adapters.home_assistant import connect_home_assistant
from floorcast.api.app_state import AppState
from floorcast.api.factories import create_app
from floorcast.domain.event_filtering import EntityBlockList
from floorcast.domain.events import EntityStateChanged, FCEvent, RegistryUpdated
from floorcast.domain.snapshot_policies import ElapsedTimePolicy
from floorcast.infrastructure.backoff import Backoff
from floorcast.infrastructure.config import Config
from floorcast.infrastructure.db import connect_db
from floorcast.infrastructure.event_bus import TypedEventBus
from floorcast.infrastructure.logging import configure_logging
from floorcast.repositories.event import EventRepository
from floorcast.repositories.snapshot import SnapshotRepository
from floorcast.server import run_websocket_server
from floorcast.services.ingestion import IngestionService
from floorcast.services.registry import RegistryService
from floorcast.services.snapshot_manager import SnapshotManager
from floorcast.services.state import StateService
from floorcast.services.websocket import WebsocketService

config = Config()  # type: ignore[call-arg]
configure_logging(config.log_level, config.log_to_console)
logger = structlog.get_logger(__name__)


async def main() -> None:
    event_bus = TypedEventBus[FCEvent]()

    async with connect_db(config.db_uri) as db_conn:
        logger.info("connected to floorcast db", db_uri=config.db_uri)

        event_repo = EventRepository(db_conn)
        snapshot_repo = SnapshotRepository(db_conn)
        state_service = StateService(snapshot_repo, event_repo)
        blocklist = EntityBlockList(config.entity_blocklist)
        registry_service = RegistryService(event_bus)

        websocket_service = WebsocketService(
            bus=event_bus, registry_service=registry_service, state_service=state_service
        )
        app_state = AppState(
            event_bus=event_bus,
            event_repo=event_repo,
            state_service=state_service,
            registry_service=registry_service,
            websocket_service=websocket_service,
        )
        app = create_app(app_state)

        snapshot_policy = ElapsedTimePolicy(config.snapshot_interval_seconds)
        ingest_service = IngestionService(
            event_bus=event_bus,
            event_repo=event_repo,
            entity_blocklist=blocklist,
        )
        snapshot_manager = SnapshotManager(
            snapshot_repo=snapshot_repo,
            state_service=state_service,
            snapshot_policy=snapshot_policy,
        )
        await snapshot_manager.initialize()

        websocket_url = config.ha_websocket_url
        websocket_token = config.ha_websocket_token

        async def ingestion_loop() -> None:
            for backoff in Backoff(2, 60):
                try:
                    async with connect_home_assistant(websocket_url, websocket_token) as client:
                        logger.info("connection to home assistant", websocket_url=websocket_url)
                        registry = await client.fetch_registry()
                        event_bus.publish(RegistryUpdated(registry=registry))
                        await ingest_service.run(client)
                        backoff.reset()
                except (ConnectionClosed, ConnectionRefusedError, OSError):
                    logger.warning("connection to home assistant lost", retry_in=backoff)
                    await asyncio.sleep(backoff.wait_seconds())

        event_bus.subscribe(EntityStateChanged, snapshot_manager.on_entity_state_changed)

        server_fn = run_websocket_server(app)
        await asyncio.gather(ingestion_loop(), server_fn)


if __name__ == "__main__":
    try:
        logger.info("starting floorcast!")
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    logger.info("floorcast stopped :(")
