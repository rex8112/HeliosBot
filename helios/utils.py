import asyncio
from typing import Awaitable, Callable, TypeVar, Any


T = TypeVar('T')


def schedule_task(seconds: int, coro: Callable[[Any], Awaitable[T]], *args, **kwargs) -> asyncio.Task[T]:
    async def task():
        await asyncio.sleep(seconds)
        return await coro(*args, **kwargs)

    return asyncio.get_event_loop().create_task(task())
