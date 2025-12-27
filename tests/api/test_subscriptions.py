import asyncio
from typing import Any
from unittest import mock

import pytest

from floorcast.api.subscriptions import Subscription, SubscriptionRegistry


class TestSubscription:
    def test_unsubscribe(self):
        mocked_unsubscribe_fn = mock.Mock()
        mocked_task = mock.Mock(spec=asyncio.Task[Any])
        subscription = Subscription(mocked_unsubscribe_fn, mocked_task)

        subscription.unsubscribe()

        mocked_unsubscribe_fn.assert_called_once()
        mocked_task.cancel.assert_called_once()


class TestSubscriptionRegistry:
    def test_unsubscribe_all(self):
        registry = SubscriptionRegistry()

        mocked_subscription1 = mock.Mock(spec=Subscription)
        mocked_subscription2 = mock.Mock(spec=Subscription)

        registry.subscribe("test1", mocked_subscription1)
        registry.subscribe("test2", mocked_subscription2)

        registry.unsubscribe_all()

        mocked_subscription1.unsubscribe.assert_called_once()
        mocked_subscription2.unsubscribe.assert_called_once()

    def test_is_subscribed(self):
        registry = SubscriptionRegistry()

        registry.subscribe("test", mock.Mock(spec=Subscription))

        assert registry.is_subscribed("test")
        assert not registry.is_subscribed("nope")

    def test_unsubscribe(self):
        registry = SubscriptionRegistry()
        registry.subscribe("test", mocked_subscription := mock.Mock(spec=Subscription))

        registry.unsubscribe("test")
        mocked_subscription.unsubscribe.assert_called_once()
        assert not registry.is_subscribed("test")

    def test_unsubscribe_unknown(self):
        registry = SubscriptionRegistry()
        with pytest.raises(ValueError, match="No subscription found for test"):
            registry.unsubscribe("test")
