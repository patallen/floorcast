from dataclasses import dataclass

import pytest

from floorcast.domain.event_filtering import EntityBlockList, FilteredEventStream


@dataclass
class FakeEvent:
    entity_id: str


class TestEntityBlockList:
    def test_should_block_exact_match(self):
        blocklist = EntityBlockList(["sensor.temperature"])
        event = FakeEvent(entity_id="sensor.temperature")

        assert blocklist.should_block(event) is True

    def test_should_not_block_non_match(self):
        blocklist = EntityBlockList(["sensor.temperature"])
        event = FakeEvent(entity_id="light.living_room")

        assert blocklist.should_block(event) is False

    def test_should_block_wildcard(self):
        blocklist = EntityBlockList(["update.*"])
        event = FakeEvent(entity_id="update.home_assistant_core")

        assert blocklist.should_block(event) is True

    def test_should_not_block_partial_wildcard_mismatch(self):
        blocklist = EntityBlockList(["update.*"])
        event = FakeEvent(entity_id="sensor.update_available")

        assert blocklist.should_block(event) is False

    def test_empty_blocklist_blocks_nothing(self):
        blocklist = EntityBlockList([])
        event = FakeEvent(entity_id="anything.here")

        assert blocklist.should_block(event) is False

    def test_multiple_patterns(self):
        blocklist = EntityBlockList(["update.*", "binary_sensor.remote_*"])

        assert blocklist.should_block(FakeEvent("update.core")) is True
        assert blocklist.should_block(FakeEvent("binary_sensor.remote_ui")) is True
        assert blocklist.should_block(FakeEvent("light.kitchen")) is False


class TestFilteredEventStream:
    @pytest.mark.asyncio
    async def test_filters_blocked_events(self):
        async def source():
            yield FakeEvent("update.core")
            yield FakeEvent("light.kitchen")
            yield FakeEvent("update.addon")
            yield FakeEvent("sensor.temp")

        blocklist = EntityBlockList(["update.*"])
        stream = FilteredEventStream(source(), blocklist)

        results = []
        async for event in stream:
            results.append(event.entity_id)
            if len(results) >= 2:
                break

        assert results == ["light.kitchen", "sensor.temp"]

    @pytest.mark.asyncio
    async def test_empty_blocklist_passes_all(self):
        async def source():
            yield FakeEvent("a")
            yield FakeEvent("b")
            yield FakeEvent("c")

        blocklist = EntityBlockList([])
        stream = FilteredEventStream(source(), blocklist)

        results = [e.entity_id async for e in stream]

        assert results == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_all_blocked_raises_stop(self):
        async def source():
            yield FakeEvent("update.a")
            yield FakeEvent("update.b")

        blocklist = EntityBlockList(["update.*"])
        stream = FilteredEventStream(source(), blocklist)

        results = [e.entity_id async for e in stream]

        assert results == []
