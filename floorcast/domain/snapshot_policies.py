from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone


class SnapshotPolicy(ABC):
    @abstractmethod
    def should_snapshot(self, events_since_snapshot: int, last_snapshot_time: datetime) -> bool:
        """Returns True if a snapshot should be taken, False otherwise."""


class ElapsedTimePolicy(SnapshotPolicy):
    """Approves snapshots when a certain amount of time has elapsed since the last snapshot."""

    def __init__(self, interval_seconds: int):
        self._interval = timedelta(seconds=interval_seconds)

    def should_snapshot(self, events_since_snapshot: int, last_snapshot_time: datetime) -> bool:
        return datetime.now(tz=timezone.utc) - last_snapshot_time >= self._interval


class EventCountPolicy(SnapshotPolicy):
    """
    Approves snapshots when a certain number of events have been processed since the last snapshot.
    """

    def __init__(self, max_events: int):
        self._max_events = max_events

    def should_snapshot(self, events_since_snapshot: int, last_snapshot_time: datetime) -> bool:
        return events_since_snapshot >= self._max_events


class HybridSnapshotPolicy(SnapshotPolicy):
    """Approves snapshots when either the event count or elapsed time policy is satisfied."""

    def __init__(self, max_events: int, interval_seconds: int):
        self._event_count_policy = EventCountPolicy(max_events)
        self._elapsed_time_policy = ElapsedTimePolicy(interval_seconds)

    def should_snapshot(self, events_since_snapshot: int, last_snapshot_time: datetime) -> bool:
        return self._event_count_policy.should_snapshot(
            events_since_snapshot, last_snapshot_time
        ) or self._elapsed_time_policy.should_snapshot(events_since_snapshot, last_snapshot_time)
