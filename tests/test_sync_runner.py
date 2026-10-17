"""core.sync_runner.SyncRunner 的单元测试。"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from core.sync_runner import SyncRunner


async def collect(runner: SyncRunner, since: int = 0) -> list[dict[str, Any]]:
    return [event async for event in runner.stream(since)]


@pytest.mark.asyncio
async def test_start_runs_and_emits_finish() -> None:
    runner = SyncRunner()

    async def run(emit: Any) -> None:
        await emit({"type": "message", "text": "hello"})

    assert runner.start(run) is True
    await runner.wait()

    assert [event["type"] for event in runner.events] == ["message", "finish"]
    assert runner.events[-1]["ok"] is True
    assert runner.busy is False
    assert runner.finished is True


@pytest.mark.asyncio
async def test_start_is_single_flight() -> None:
    runner = SyncRunner()
    gate = asyncio.Event()

    async def run(emit: Any) -> None:
        await gate.wait()

    assert runner.start(run) is True
    assert runner.start(run) is False
    assert runner.busy is True

    gate.set()
    await runner.wait()

    assert runner.busy is False
    assert runner.start(lambda emit: asyncio.sleep(0)) is True
    await runner.wait()


@pytest.mark.asyncio
async def test_stream_replays_finished_run() -> None:
    runner = SyncRunner()

    async def run(emit: Any) -> None:
        await emit({"type": "message", "text": "first"})
        await emit({"type": "message", "text": "second"})

    runner.start(run)
    await runner.wait()

    events = await collect(runner)
    assert [event["text"] for event in events if event["type"] == "message"] == [
        "first",
        "second",
    ]
    assert events[-1]["type"] == "finish"

    tail = await collect(runner, since=1)
    assert [event["seq"] for event in tail] == [2, 3]


@pytest.mark.asyncio
async def test_stream_receives_live_events() -> None:
    runner = SyncRunner()
    task = asyncio.create_task(collect(runner))
    await asyncio.sleep(0)

    async def run(emit: Any) -> None:
        await emit({"type": "message", "text": "live"})

    runner.start(run)
    await runner.wait()
    events = await task

    assert [event["type"] for event in events] == ["message", "finish"]


@pytest.mark.asyncio
async def test_exception_emits_failed_finish(caplog: Any) -> None:
    runner = SyncRunner()

    async def run(emit: Any) -> None:
        raise RuntimeError("boom")

    runner.start(run)
    await runner.wait()

    last = runner.events[-1]
    assert last["type"] == "finish"
    assert last["ok"] is False
    assert last["reason"] == "error"
    assert "boom" in last["error"]
    assert "boom" in caplog.text


@pytest.mark.asyncio
async def test_run_without_finish_gets_default_finish() -> None:
    runner = SyncRunner()

    async def run(emit: Any) -> None:
        await emit({"type": "message", "text": "only"})

    runner.start(run)
    await runner.wait()

    assert runner.events[-1]["type"] == "finish"
    assert runner.events[-1]["ok"] is True
    assert runner.events[-1]["reason"] == "done"


@pytest.mark.asyncio
async def test_close_cancels_busy_run_and_wakes_stream() -> None:
    runner = SyncRunner()
    gate = asyncio.Event()

    async def run(emit: Any) -> None:
        await gate.wait()

    runner.start(run)
    task = asyncio.create_task(collect(runner))
    await asyncio.sleep(0)

    await runner.close()
    events = await task

    assert events[-1]["type"] == "finish"
    assert events[-1]["ok"] is False
    assert events[-1]["reason"] == "cancelled"
    assert runner.busy is False
    await runner.wait()  # 已结束的任务不应再次阻塞


@pytest.mark.asyncio
async def test_buffer_keeps_only_latest_events() -> None:
    runner = SyncRunner(buffer_size=3)

    async def run(emit: Any) -> None:
        for index in range(5):
            await emit({"type": "message", "text": str(index)})

    runner.start(run)
    await runner.wait()

    assert [event["text"] for event in runner.events if event["type"] == "message"] == [
        "3",
        "4",
    ]


@pytest.mark.asyncio
async def test_stream_unsubscribes_on_exit() -> None:
    runner = SyncRunner()

    async def run(emit: Any) -> None:
        await emit({"type": "message", "text": "x"})

    runner.start(run)
    await runner.wait()
    await collect(runner)

    assert runner._subscribers == set()


@pytest.mark.asyncio
async def test_wait_without_task_returns_immediately() -> None:
    await SyncRunner().wait()


@pytest.mark.asyncio
async def test_close_after_finished_is_noop() -> None:
    runner = SyncRunner()

    async def run(emit: Any) -> None:
        await emit({"type": "message", "text": "x"})

    runner.start(run)
    await runner.wait()
    await runner.close()

    assert runner.busy is False


@pytest.mark.asyncio
async def test_close_wakes_idle_stream() -> None:
    runner = SyncRunner()
    task = asyncio.create_task(collect(runner))
    await asyncio.sleep(0)

    await runner.close()

    assert await task == []


@pytest.mark.asyncio
async def test_stream_since_beyond_buffer_returns_for_finished_run() -> None:
    runner = SyncRunner()

    async def run(emit: Any) -> None:
        await emit({"type": "message", "text": "x"})

    runner.start(run)
    await runner.wait()

    assert await collect(runner, since=99) == []
