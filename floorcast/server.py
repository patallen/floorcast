import uvicorn
from fastapi import FastAPI


async def run_websocket_server(app: FastAPI) -> None:
    server_config = uvicorn.Config(
        app, host="0.0.0.0", port=8000, log_level="warning", access_log=False
    )
    server = uvicorn.Server(server_config)
    await server.serve()
