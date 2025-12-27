import asyncio
from typing import Any, Coroutine, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


def create_logged_task(
    coro: Coroutine[Any, Any, T], *, name: str | None = None
) -> asyncio.Task[Any]:
    """Creates a task that logs exceptions on failure.

    Asyncio tasks are hungry hippos that love to swallow errors. This function wraps the provided
    coroutine and logs exceptions before re-raising them.
    """
    task_name = name or coro.__qualname__

    async def wrapper() -> T:
        try:
            return await coro
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(f"Task '{task_name}' failed")
            raise

    return asyncio.create_task(wrapper(), name=task_name)


__all__ = ["create_logged_task"]
