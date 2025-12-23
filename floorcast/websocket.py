import json

import structlog
from websockets import ClientConnection, connect

logger = structlog.get_logger(__name__)


class HomeAssistantAuth:
    def __init__(self, token: str):
        self.token = token

    async def authenticate(self, ws: ClientConnection) -> bool:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": self.token}))
        response = json.loads(await ws.recv())
        return response.get("type") == "auth_ok"


class HomeAssistantWebsocket:
    def __init__(
        self, url: str, auth: HomeAssistantAuth, event_types: list[str] = None
    ):
        self._event_types = event_types
        self._auth = auth
        self._url = url
        self._socket = None

    async def _subscribe_events(self):
        payload = {"id": 1, "type": "subscribe_events", "event_type": "state_changed"}
        await self._socket.send(json.dumps(payload))

    async def __aenter__(self):
        self._socket = await connect(self._url)
        await self._auth.authenticate(self._socket)
        await self._subscribe_events()
        return self

    async def __aiter__(self):
        while True:
            yield json.loads(await self._socket.recv())

    async def __aexit__(self, exc_type, exc, tb):
        await self._socket.close()
        self._socket = None
