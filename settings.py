from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FLOORCAST_")

    ha_ws_token: str
    ha_url: str = "http://homeassistant.local:8123"
    db_uri: str = "floorcast.db"
