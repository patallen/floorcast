import uuid
from datetime import datetime, timezone
from unittest import mock

import pytest

from floorcast.domain.models import Event, Snapshot
from floorcast.services.state import StateService


@pytest.fixture
def snapshot_repo():
    return mock.AsyncMock()


@pytest.fixture
def event_repo():
    return mock.AsyncMock()


def make_event(**overrides):
    data = {
        "domain": "light",
        "external_id": "fake",
        "event_id": uuid.uuid4(),
        "event_type": "who cares",
        "timestamp": datetime.now(timezone.utc),
        "data": {},
        **overrides,
    }
    return Event(**data)


@pytest.mark.asyncio
async def test_get_state_at(snapshot_repo, event_repo):
    snapshot_repo.get_before_timestamp.return_value = Snapshot(
        last_event_id=1, state={"a.id": {"value": 1, "unit": "m"}}
    )
    event_repo.get_between_id_and_timestamp.return_value = [
        make_event(id=2, entity_id="a.id", state="2", unit="m"),
        make_event(id=3, entity_id="b.id", state="3", unit="m"),
    ]
    service = StateService(snapshot_repo=snapshot_repo, event_repo=event_repo)
    as_of_timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
    state = await service.get_state_at(as_of_timestamp)
    assert state.last_event_id == 3
    assert state.state["a.id"] == {"value": "2", "unit": "m"}
    assert state.state["b.id"] == {"value": "3", "unit": "m"}
    assert list(state.state.keys()) == ["a.id", "b.id"]
