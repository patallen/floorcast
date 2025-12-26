# Floorcast

Home Assistant event logger with DVR-style timeline playback. Captures entity state changes via WebSocket, persists to SQLite, serves a React frontend for real-time monitoring and historical scrubbing.

## Local Development

```bash
# Backend
uv sync
cp .env.example .env  # fill in HA token
uv run uvicorn floorcast.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173
Backend: http://localhost:8000

## Configuration

Create `.env` with:

```
FLOORCAST_HA_WEBSOCKET_URL=ws://homeassistant.local:8123/api/websocket
FLOORCAST_HA_WEBSOCKET_TOKEN=<long-lived access token from HA>
FLOORCAST_DB_URI=floorcast.db
FLOORCAST_ENTITY_BLOCKLIST=["update.*"]
```

Get a token from HA: Profile → Security → Long-Lived Access Tokens

## Architecture

- **Backend**: FastAPI, WebSocket at `/events/live`, REST at `/timeline`
- **Frontend**: React/Vite, single-page with canvas-based timeline
- **Data**: SQLite with snapshots for state reconstruction
