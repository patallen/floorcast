from collections import defaultdict

from floorcast.domain.events import EntityStateChanged, FCEvent
from floorcast.domain.ports import EventPublisher, RegistryStore, StateReconstructor
from floorcast.domain.websocket import WSConnection, WSMessage


class WebsocketService:
    def __init__(
        self,
        bus: EventPublisher[FCEvent],
        state_service: StateReconstructor,
        registry_service: RegistryStore,
    ) -> None:
        self._bus = bus
        self._registry_service = registry_service
        self._state_service = state_service
        self._clients: set[WSConnection] = set()
        self._subscriptions: dict[str, set[WSConnection]] = defaultdict(set)
        self._unsubscribe_from_state_changes = bus.subscribe(
            EntityStateChanged, self._handle_entity_state_change_event
        )

    async def _handle_entity_state_change_event(self, event: EntityStateChanged) -> None:
        entity_state_subscriptions = self._subscriptions["entity_states"]
        for client in self._clients:
            if client in entity_state_subscriptions:
                client.queue.put_nowait(
                    WSMessage(
                        type="entity.state_change",
                        data={
                            "id": event.event.id,
                            "timestamp": int(event.event.timestamp.timestamp() * 1000),
                            "state": event.state,
                            "entity_id": event.event.entity_id,
                            "unit": event.event.unit,
                        },
                    )
                )

    def connect(self) -> WSConnection:
        conn = WSConnection()
        self._clients.add(conn)
        return conn

    def disconnect(self, conn: WSConnection) -> None:
        self._clients.discard(conn)

    def send_message(self, conn: WSConnection, message: WSMessage) -> None:
        match message.type:
            case "subscribe":
                assert isinstance(message.data, str)
                self._handle_subscribe(conn, message.data)
            case "unsubscribe":
                assert isinstance(message.data, str)
                self._handle_unsubscribe(conn, message.data)
            case "ping":
                self._handle_ping(conn)
            case _:
                raise ValueError(f"Unknown message type: {message.type}")

    @staticmethod
    def _handle_ping(conn: WSConnection) -> None:
        conn.queue.put_nowait(WSMessage(type="pong"))

    def _handle_subscribe(self, conn: WSConnection, subscription: str) -> None:
        if subscription not in ("entity_states",):
            raise ValueError(f"Unknown subscription: {subscription}")
        self._subscriptions[subscription].add(conn)

    def _handle_unsubscribe(self, conn: WSConnection, subscription: str) -> None:
        if subscription not in ("entity_states",):
            raise ValueError(f"Unknown subscription: {subscription}")
        self._subscriptions[subscription].discard(conn)

    async def request_registry(self, conn: WSConnection) -> None:
        registry = self._registry_service.get_registry()
        conn.queue.put_nowait(WSMessage(type="registry", data=registry.to_dict()))

    async def request_snapshot(self, conn: WSConnection) -> None:
        from datetime import datetime, timezone

        state = await self._state_service.get_state_at(datetime.now(tz=timezone.utc))
        conn.queue.put_nowait(
            WSMessage(
                type="snapshot",
                data=state.state,
            )
        )
