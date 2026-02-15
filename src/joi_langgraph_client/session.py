import asyncio
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any


class ApprovalGate:
    def __init__(self):
        self._pending: dict[str, asyncio.Event] = {}
        self._results: dict[str, bool] = {}

    async def wait(self, key: str, timeout: float = 300) -> bool:
        event = asyncio.Event()
        self._pending[key] = event
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return self._results.pop(key, False)
        except TimeoutError:
            return False
        finally:
            self._pending.pop(key, None)

    def resolve(self, key: str, approved: bool) -> None:
        self._results[key] = approved
        event = self._pending.get(key)
        if event:
            event.set()


class MessageDebouncer:
    def __init__(self, timeout: float = 1.5):
        self._timeout = timeout
        self._pending: dict[str, tuple[asyncio.Task, list[str], Any]] = {}

    async def add(
        self,
        key: str,
        text: str,
        context: Any,
        callback: Callable[[str, Any], Awaitable[None]],
    ) -> None:
        if key in self._pending:
            task, messages, _ = self._pending[key]
            task.cancel()
            messages.append(text)
        else:
            messages = [text]

        async def fire():
            await asyncio.sleep(self._timeout)
            data = self._pending.pop(key, None)
            if data:
                _, msgs, ctx = data
                await callback("\n".join(msgs), ctx)

        self._pending[key] = (asyncio.create_task(fire()), messages, context)


@asynccontextmanager
async def periodic_callback(fn: Callable[[], Awaitable[None]], interval: float = 4.0):
    async def loop():
        while True:
            await fn()
            await asyncio.sleep(interval)

    task = asyncio.create_task(loop())
    try:
        yield
    finally:
        task.cancel()


def make_thread_id(channel: str, user_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{channel}-{user_id}"))
