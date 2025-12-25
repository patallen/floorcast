from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FLOORCAST_")

    snapshot_interval_seconds: int = 300
    ha_websocket_token: str
    ha_websocket_url: str = "ws://homeassistant.local:8123/api/websocket"
    db_uri: str = "floorcast.db"

    entity_blocklist: list[str] = ["update.*"]
    log_level: str = "INFO"
    log_to_console: bool = False
