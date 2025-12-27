import asyncio
from unittest.mock import patch

import pytest

from floorcast.common.aio import create_logged_task


@pytest.mark.asyncio
async def test_task_returns_result():
    async def my_coro():
        return 42

    task = create_logged_task(my_coro())
    result = await task

    assert result == 42


@pytest.mark.asyncio
async def test_task_uses_coro_qualname_by_default():
    async def my_coro():
        return None

    task = create_logged_task(my_coro())
    await task

    assert task.get_name().endswith("my_coro")


@pytest.mark.asyncio
async def test_task_uses_explicit_name_when_provided():
    async def my_coro():
        return None

    task = create_logged_task(my_coro(), name="custom_name")
    await task

    assert task.get_name() == "custom_name"


@pytest.mark.asyncio
async def test_exception_is_logged():
    async def failing_coro():
        raise ValueError("boom")

    with patch("floorcast.common.aio.logger") as mock_logger:
        task = create_logged_task(failing_coro())

        with pytest.raises(ValueError, match="boom"):
            await task

        mock_logger.exception.assert_called_once()
        assert "failing_coro" in str(mock_logger.exception.call_args)


@pytest.mark.asyncio
async def test_exception_is_reraised():
    async def failing_coro():
        raise ValueError("boom")

    task = create_logged_task(failing_coro())

    with pytest.raises(ValueError, match="boom"):
        await task


@pytest.mark.asyncio
async def test_cancelled_error_is_not_logged():
    async def cancellable_coro():
        await asyncio.sleep(10)

    with patch("floorcast.common.aio.logger") as mock_logger:
        task = create_logged_task(cancellable_coro())

        await asyncio.sleep(0)  # let task start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        mock_logger.exception.assert_not_called()


@pytest.mark.asyncio
async def test_cancelled_error_is_propagated():
    async def cancellable_coro():
        await asyncio.sleep(10)

    task = create_logged_task(cancellable_coro())

    await asyncio.sleep(0)  # let task start
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
