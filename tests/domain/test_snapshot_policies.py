from datetime import datetime, timedelta, timezone

from floorcast.domain.snapshot_policies import (
    ElapsedTimePolicy,
    EventCountPolicy,
    HybridSnapshotPolicy,
)


class TestHybridSnapshotPolicy:
    def test_snapshots_if_over_max_events(self):
        policy = HybridSnapshotPolicy(max_events=10, interval_seconds=60)
        assert policy.should_snapshot(10, datetime.now(tz=timezone.utc))
        assert policy.should_snapshot(11, datetime.now(tz=timezone.utc))

    def test_does_not_snapshot_if_under_max_events(self):
        policy = HybridSnapshotPolicy(max_events=10, interval_seconds=60)
        assert not policy.should_snapshot(9, datetime.now(tz=timezone.utc))

    def test_snapshots_if_over_max_interval(self):
        previous_snapshot_time = datetime.now(tz=timezone.utc) - timedelta(seconds=61)
        policy = HybridSnapshotPolicy(max_events=100, interval_seconds=60)
        assert policy.should_snapshot(0, previous_snapshot_time)

    def test_does_not_snapshot_if_under_max_interval(self):
        previous_snapshot_time = datetime.now(tz=timezone.utc) - timedelta(seconds=59)
        policy = HybridSnapshotPolicy(max_events=10, interval_seconds=60)
        assert not policy.should_snapshot(0, previous_snapshot_time)


class TestElapsedTimePolicy:
    def test_snapshots_if_over_max_interval(self):
        previous_snapshot_time = datetime.now(tz=timezone.utc) - timedelta(seconds=61)
        policy = ElapsedTimePolicy(interval_seconds=60)
        assert policy.should_snapshot(0, previous_snapshot_time)

    def test_does_not_snapshot_if_under_max_interval(self):
        previous_snapshot_time = datetime.now(tz=timezone.utc) - timedelta(seconds=59)
        policy = ElapsedTimePolicy(interval_seconds=60)
        assert not policy.should_snapshot(0, previous_snapshot_time)


class TestEventCountPolicy:
    def test_snapshots_if_over_max_events(self):
        policy = EventCountPolicy(max_events=10)
        assert policy.should_snapshot(10, datetime.now(tz=timezone.utc))
        assert policy.should_snapshot(11, datetime.now(tz=timezone.utc))

    def test_does_not_snapshot_if_under_max_events(self):
        policy = EventCountPolicy(max_events=10)
        assert not policy.should_snapshot(9, datetime.now(tz=timezone.utc))
