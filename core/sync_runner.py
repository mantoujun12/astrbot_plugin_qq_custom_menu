"""后台同步任务与 SSE 事件缓冲。

Dashboard 的同步入口返回后任务继续在后台执行，进度通过 ``stream()`` 以
结构化事件推送。事件带单调递增的 ``seq``，断线重连时可用 ``since`` 续订。
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from astrbot.api import logger

from .i18n import LOG_TAG

EmitCallback = Callable[[dict[str, Any]], Awaitable[None]]
RunCallback = Callable[[EmitCallback], Awaitable[Any]]

DEFAULT_EVENT_BUFFER = 200


class SyncRunner:
    """单飞（single-flight）同步任务执行器。"""

    def __init__(self, buffer_size: int = DEFAULT_EVENT_BUFFER) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max(1, buffer_size))
        self._subscribers: set[asyncio.Queue[dict[str, Any] | None]] = set()
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._seq = 0
        self._busy = False
        # 从未启动时为 False：此时建立的 SSE 流应保持等待，任务一启动就能收到事件。
        self._finished = False

    @property
    def busy(self) -> bool:
        """是否有同步任务正在执行。"""
        return self._busy

    @property
    def finished(self) -> bool:
        """最近一轮任务是否已经结束；从未启动时为 False（流会继续等待）。"""
        return self._finished

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        """当前事件缓冲区快照，主要供测试与调试使用。"""
        return tuple(self._events)

    def start(self, run: RunCallback) -> bool:
        """启动一轮任务；已有任务在跑时返回 False，不排队。"""
        if self._busy:
            return False
        self._busy = True
        self._finished = False
        self._seq = 0
        self._events.clear()
        self._task = asyncio.create_task(self._run(run))
        return True

    async def wait(self) -> None:
        """等待当前任务结束（测试与关停流程使用）。"""
        task = self._task
        if task is None:
            return
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            # close() 主动取消的任务已经由 _run 发出 finish 事件，这里视为正常结束；
            # 若取消的是调用方自己，则继续向上传播。
            if not task.cancelled():
                raise

    async def close(self) -> None:
        """取消正在执行的任务并唤醒所有订阅者。"""
        task = self._task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        async with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            queue.put_nowait(None)

    async def emit(self, event: dict[str, Any]) -> None:
        """追加一条事件并广播给所有订阅者。"""
        async with self._lock:
            self._seq += 1
            payload = {**event, "seq": self._seq}
            self._events.append(payload)
            subscribers = list(self._subscribers)
        for queue in subscribers:
            queue.put_nowait(payload)

    async def stream(self, since: int = 0) -> AsyncIterator[dict[str, Any]]:
        """回放 ``since`` 之后的事件并持续推送新事件，遇到 finish 后结束。"""
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
            replay = [event for event in self._events if event["seq"] > since]
            finished = self._finished

        try:
            for event in replay:
                yield event
                if event.get("type") == "finish":
                    return
            if finished:
                return

            while True:
                event = await queue.get()
                if event is None:
                    return
                yield event
                if event.get("type") == "finish":
                    return
        finally:
            async with self._lock:
                self._subscribers.discard(queue)

    def _last_is_finish(self) -> bool:
        return bool(self._events) and self._events[-1].get("type") == "finish"

    async def _emit_finish(self, *, ok: bool, reason: str, error: str = "") -> None:
        if self._last_is_finish():
            return
        await self.emit(
            {
                "type": "finish",
                "ok": ok,
                "reason": reason,
                "platforms": 0,
                "succeeded": 0,
                "failed": 0,
                "error": error,
            }
        )

    async def _run(self, run: RunCallback) -> None:
        try:
            await run(self.emit)
            await self._emit_finish(ok=True, reason="done")
        except asyncio.CancelledError:
            await self._emit_finish(ok=False, reason="cancelled", error="cancelled")
            raise
        except Exception as exc:
            logger.error("%s sync run failed: %s", LOG_TAG, exc, exc_info=True)
            await self._emit_finish(ok=False, reason="error", error=str(exc))
        finally:
            async with self._lock:
                self._busy = False
                self._finished = True


__all__ = ["DEFAULT_EVENT_BUFFER", "EmitCallback", "RunCallback", "SyncRunner"]
