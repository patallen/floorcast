from __future__ import annotations

import asyncio
from typing import Any, Callable


class Subscription:
    def __init__(self, unsubscribe_fn: Callable[[], None], task: asyncio.Task[Any]) -> None:
        self._unsubscribe_fn = unsubscribe_fn
        self._task = task

    def unsubscribe(self) -> None:
        self._unsubscribe_fn()
        self._task.cancel()


class SubscriptionRegistry:
    def __init__(self) -> None:
        self._subscriptions: dict[str, Subscription] = {}

    def is_subscribed(self, name: str) -> bool:
        return name in self._subscriptions

    def unsubscribe(self, name: str) -> None:
        subscription = self._subscriptions.pop(name, None)
        if not subscription:
            raise ValueError(f"No subscription found for {name}")
        subscription.unsubscribe()

    def subscribe(self, name: str, subscription: Subscription) -> None:
        self._subscriptions[name] = subscription

    def unsubscribe_all(self) -> None:
        for subscription in self._subscriptions.values():
            subscription.unsubscribe()
