from unittest.mock import patch

import pytest
from pydantic import ValidationError

from floorcast.infrastructure.config import Config


def test_defaults():
    with patch.dict("os.environ", {"FLOORCAST_HA_WEBSOCKET_TOKEN": "secret"}, clear=True):
        # _env_file=None ensures the local env file is not used
        config = Config(_env_file=None)

    assert config.snapshot_interval_seconds == 300
    assert config.ha_websocket_url == "ws://homeassistant.local:8123/api/websocket"
    assert config.db_uri == "floorcast.db"
    assert config.entity_blocklist == ["update.*"]
    assert config.log_level == "INFO"
    assert config.log_to_console is False


def test_ha_websocket_token_required():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValidationError):
            # _env_file=None ensures the local env file is not used
            Config(_env_file=None)


def test_env_overrides():
    env = {
        "FLOORCAST_HA_WEBSOCKET_TOKEN": "my-token",
        "FLOORCAST_HA_WEBSOCKET_URL": "ws://custom:8123/api/websocket",
        "FLOORCAST_DB_URI": "custom.db",
        "FLOORCAST_SNAPSHOT_INTERVAL_SECONDS": "60",
        "FLOORCAST_ENTITY_BLOCKLIST": '["sensor.*", "binary_sensor.*"]',
        "FLOORCAST_LOG_LEVEL": "DEBUG",
        "FLOORCAST_LOG_TO_CONSOLE": "true",
    }
    with patch.dict("os.environ", env, clear=True):
        # _env_file=None ensures the local env file is not used
        config = Config()

    assert config.ha_websocket_token == "my-token"
    assert config.ha_websocket_url == "ws://custom:8123/api/websocket"
    assert config.db_uri == "custom.db"
    assert config.snapshot_interval_seconds == 60
    assert config.entity_blocklist == ["sensor.*", "binary_sensor.*"]
    assert config.log_level == "DEBUG"
    assert config.log_to_console is True
