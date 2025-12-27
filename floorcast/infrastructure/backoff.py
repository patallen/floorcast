from __future__ import annotations


class Backoff:
    def __init__(self, initial: int, limit: int) -> None:
        self._initial = initial
        self._limit = limit
        self._current = initial

    def reset(self) -> None:
        self._current = self._initial

    def wait_seconds(self) -> float:
        return self._current

    def __iter__(self) -> Backoff:
        return self

    def __next__(self) -> "Backoff":
        self._current = min(self._initial * 2, self._limit)
        return self
