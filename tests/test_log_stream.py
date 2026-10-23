"""core.log_stream 的日志采集、回放与实时订阅测试。"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from core.i18n import LOG_TAG, t
from core.log_stream import (
    MAX_LOG_ENTRY_CHARS,
    LogBuffer,
    LogEntry,
    LogSubscriberLimitError,
)


def make_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"test-log-stream-{name}")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger


async def first_entry(buffer: LogBuffer, since: int = 0) -> LogEntry | None:
    stream = buffer.follow(since, heartbeat_seconds=10)
    try:
        return await asyncio.wait_for(anext(stream), timeout=1)
    finally:
        await stream.aclose()


def test_log_entry_as_event_includes_optional_traceback() -> None:
    entry = LogEntry(
        seq=3,
        timestamp="2026-10-23T00:00:00.000Z",
        level="error",
        message="failed",
        traceback="RuntimeError: boom",
    )

    assert entry.as_event()["traceback"] == "RuntimeError: boom"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"capacity": 0},
        {"heartbeat_seconds": 0},
        {"max_subscribers": 0},
    ],
)
def test_invalid_limits_are_rejected(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        LogBuffer(**kwargs)


@pytest.mark.asyncio
async def test_install_filters_prefix_and_formats_record() -> None:
    buffer = LogBuffer()
    logger = make_logger("format")
    buffer.install(logger)
    try:
        logger.info("%s plugin booted", LOG_TAG)
    finally:
        buffer.close()

    entry = await first_entry(buffer)

    assert entry is not None
    assert entry.seq == 1
    assert entry.level == "info"
    assert entry.message == "plugin booted"
    assert entry.timestamp.endswith("Z")


@pytest.mark.asyncio
async def test_plugin_records_without_prefix_are_kept() -> None:
    buffer = LogBuffer()
    logger = make_logger("unprefixed")
    buffer.install(logger)
    try:
        logger.warning("readable legacy message")
    finally:
        buffer.close()

    entry = await first_entry(buffer)

    assert entry is not None
    assert entry.message == "readable legacy message"


def test_install_supports_loguru_logger_and_captures_debug() -> None:
    class FakeLoguruLogger:
        def __init__(self) -> None:
            self.sink: Any = None
            self.filter: Any = None
            self.level: str | None = None
            self.removed: int | None = None

        def add(self, sink: Any, *, level: str, filter: Any) -> int:  # noqa: A002
            self.sink = sink
            self.filter = filter
            self.level = level
            return 42

        def remove(self, sink_id: int) -> None:
            self.removed = sink_id

    logger = FakeLoguruLogger()
    buffer = LogBuffer()
    buffer.install(logger)
    try:
        source = SimpleNamespace(path=str(Path(__file__).resolve()))
        record = {
            "file": source,
            "level": SimpleNamespace(no=logging.DEBUG),
            "name": "core.menu",
            "line": 20,
            "message": f"{LOG_TAG} debug details",
            "function": "sync",
            "exception": None,
            "time": datetime.now(timezone.utc),  # noqa: UP017 - Python 3.10 compatibility
        }
        assert logger.level == "DEBUG"
        assert logger.filter(record)
        logger.sink(SimpleNamespace(record=record))
    finally:
        buffer.close()

    entry = asyncio.run(first_entry(buffer))
    assert logger.removed == 42
    assert entry is not None
    assert entry.level == "debug"
    assert entry.message == "debug details"


def test_install_rejects_unsupported_logger() -> None:
    buffer = LogBuffer()

    with pytest.raises(TypeError, match="addHandler"):
        buffer.install(object())

    assert buffer.last_seq == 0


def test_install_targets_shared_logger_not_caller_module() -> None:
    """AstrBot 4.29+ 的 logger 代理必须解析到真正的共享 logger。"""

    shared = make_logger("proxy-shared")
    caller = make_logger("proxy-caller")

    class CallerAwareLoggerProxy:
        def __init__(self) -> None:
            self.targets: dict[str, logging.Logger] = {}
            self.fallback = caller

        def __getattr__(self, item: str) -> Any:
            if item == "name":
                return shared.name
            module_name = sys._getframe(1).f_globals.get("__name__", "")
            return getattr(self.targets.get(module_name, self.fallback), item)

    proxy = CallerAwareLoggerProxy()
    assert not isinstance(proxy, logging.Logger)
    assert not hasattr(caller, "add")

    buffer = LogBuffer()
    buffer.install(proxy)
    try:
        assert len(shared.handlers) == 1
        assert caller.handlers == []
        shared.info("%s via shared logger", LOG_TAG)
    finally:
        buffer.close()

    assert shared.handlers == []
    assert caller.handlers == []
    entry = asyncio.run(first_entry(buffer))
    assert entry is not None
    assert entry.message == "via shared logger"


def test_same_prefix_from_another_plugin_is_not_captured(tmp_path: Path) -> None:
    buffer = LogBuffer()
    outside_record = logging.LogRecord(
        name="another-plugin",
        level=logging.INFO,
        pathname=str(tmp_path / "another_plugin.py"),
        lineno=1,
        msg=f"{LOG_TAG} should not be captured",
        args=(),
        exc_info=None,
    )

    buffer.add_record(outside_record)

    assert buffer.last_seq == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "level"),
    [
        ("debug", "debug"),
        ("info", "info"),
        ("warning", "warning"),
        ("error", "error"),
        ("critical", "critical"),
    ],
)
async def test_levels_are_normalized(method: str, level: str) -> None:
    buffer = LogBuffer()
    logger = make_logger(f"level-{level}")
    buffer.install(logger)
    try:
        getattr(logger, method)(f"{LOG_TAG} level message")
    finally:
        buffer.close()

    entry = await first_entry(buffer)

    assert entry is not None
    assert entry.level == level


@pytest.mark.asyncio
async def test_exception_traceback_is_captured() -> None:
    buffer = LogBuffer()
    logger = make_logger("traceback")
    buffer.install(logger)
    try:
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            logger.exception(f"{LOG_TAG} failed")
    finally:
        buffer.close()

    entry = await first_entry(buffer)

    assert entry is not None
    assert "Traceback" in entry.traceback
    assert "RuntimeError: boom" in entry.traceback


@pytest.mark.asyncio
async def test_stack_info_is_captured() -> None:
    buffer = LogBuffer()
    logger = make_logger("stack")
    buffer.install(logger)
    try:
        logger.info(f"{LOG_TAG} with stack", stack_info=True)
    finally:
        buffer.close()

    entry = await first_entry(buffer)

    assert entry is not None
    assert "Stack (most recent call last)" in entry.traceback


@pytest.mark.asyncio
async def test_buffer_keeps_latest_entries_with_monotonic_seq() -> None:
    buffer = LogBuffer(capacity=2)
    logger = make_logger("capacity")
    buffer.install(logger)
    try:
        logger.info(f"{LOG_TAG} one")
        logger.info(f"{LOG_TAG} two")
        logger.info(f"{LOG_TAG} three")
    finally:
        buffer.close()

    entry = await first_entry(buffer)

    assert buffer.last_seq == 3
    assert entry is not None
    assert entry.seq == 2
    assert entry.message == "two"


@pytest.mark.asyncio
async def test_follow_since_replays_only_newer_entries() -> None:
    buffer = LogBuffer(capacity=3)
    logger = make_logger("since")
    buffer.install(logger)
    try:
        logger.info(f"{LOG_TAG} one")
        logger.info(f"{LOG_TAG} two")
        logger.info(f"{LOG_TAG} three")
    finally:
        buffer.close()

    entry = await first_entry(buffer, since=2)

    assert entry is not None
    assert entry.seq == 3
    assert entry.message == "three"


@pytest.mark.asyncio
async def test_follow_receives_live_entries_and_supports_multiple_subscribers() -> None:
    buffer = LogBuffer()
    logger = make_logger("live")
    buffer.install(logger)
    first = buffer.follow(0, heartbeat_seconds=10)
    second = buffer.follow(0, heartbeat_seconds=10)
    first_next = asyncio.create_task(anext(first))
    second_next = asyncio.create_task(anext(second))
    await asyncio.sleep(0)

    try:
        logger.info(f"{LOG_TAG} live")
        one, two = await asyncio.wait_for(asyncio.gather(first_next, second_next), timeout=1)
    finally:
        await first.aclose()
        await second.aclose()
        buffer.close()

    assert one is not None and two is not None
    assert one.seq == two.seq == 1
    assert one.message == two.message == "live"


@pytest.mark.asyncio
async def test_install_does_not_replace_an_active_buffer_handler() -> None:
    logger = make_logger("replace")
    first_buffer = LogBuffer()
    first_buffer.install(logger)
    stream = first_buffer.follow(0, heartbeat_seconds=10)
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)

    second_buffer = LogBuffer()
    second_buffer.install(logger)
    assert len(logger.handlers) == 2
    first_buffer.close()

    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(pending, timeout=1)
    await stream.aclose()

    try:
        logger.info(f"{LOG_TAG} after replacement")
    finally:
        second_buffer.close()

    entry = await first_entry(second_buffer)
    assert len(logger.handlers) == 0
    assert entry is not None
    assert entry.message == "after replacement"


@pytest.mark.asyncio
async def test_follow_limits_concurrent_subscribers() -> None:
    buffer = LogBuffer(max_subscribers=1)
    first = buffer.follow()
    pending = asyncio.create_task(anext(first))
    await asyncio.sleep(0)
    second = buffer.follow()

    with pytest.raises(LogSubscriberLimitError):
        await anext(second)

    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    await first.aclose()
    buffer.close()


@pytest.mark.asyncio
async def test_follow_rejects_non_positive_heartbeat() -> None:
    stream = LogBuffer().follow(heartbeat_seconds=0)

    with pytest.raises(ValueError):
        await anext(stream)

    await stream.aclose()


@pytest.mark.asyncio
async def test_follow_is_woken_by_logs_from_worker_threads() -> None:
    buffer = LogBuffer()
    logger = make_logger("thread")
    buffer.install(logger)
    stream = buffer.follow(0, heartbeat_seconds=10)
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)

    def log_from_plugin_thread() -> None:
        logger.info(f"{LOG_TAG} from thread")

    try:
        await asyncio.to_thread(log_from_plugin_thread)
        entry = await asyncio.wait_for(pending, timeout=1)
    finally:
        await stream.aclose()
        buffer.close()

    assert entry is not None
    assert entry.message == "from thread"


@pytest.mark.asyncio
async def test_close_removes_handler_and_ends_waiting_stream() -> None:
    buffer = LogBuffer()
    logger = make_logger("close")
    buffer.install(logger)
    assert len(logger.handlers) == 1

    stream = buffer.follow(0, heartbeat_seconds=10)
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    buffer.close()

    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(pending, timeout=1)
    await stream.aclose()

    assert logger.handlers == []


def test_closed_buffer_ignores_new_records() -> None:
    buffer = LogBuffer()
    buffer.close()
    record = logging.LogRecord(
        name="closed",
        level=logging.INFO,
        pathname=str(Path(__file__).resolve()),
        lineno=1,
        msg=f"{LOG_TAG} ignored",
        args=(),
        exc_info=None,
    )

    buffer.add_record(record)

    assert buffer.last_seq == 0


@pytest.mark.asyncio
async def test_oversized_entry_is_truncated() -> None:
    buffer = LogBuffer()
    logger = make_logger("truncate")
    buffer.install(logger)
    try:
        logger.info(f"{LOG_TAG} {'x' * (MAX_LOG_ENTRY_CHARS + 100)}")
    finally:
        buffer.close()

    entry = await first_entry(buffer)

    assert entry is not None
    assert len(entry.message) == MAX_LOG_ENTRY_CHARS
    assert entry.message.endswith(t("log.stream_entry_truncated"))


@pytest.mark.asyncio
async def test_oversized_traceback_is_truncated() -> None:
    buffer = LogBuffer()
    logger = make_logger("traceback-truncate")
    buffer.install(logger)
    try:
        try:
            raise RuntimeError("x" * (MAX_LOG_ENTRY_CHARS + 100))
        except RuntimeError:
            logger.exception(f"{LOG_TAG} failed")
    finally:
        buffer.close()

    entry = await first_entry(buffer)

    assert entry is not None
    assert entry.traceback.endswith(t("log.stream_entry_truncated"))
    assert len(entry.message) + len(entry.traceback) <= MAX_LOG_ENTRY_CHARS


@pytest.mark.asyncio
async def test_follow_emits_heartbeat_when_idle() -> None:
    buffer = LogBuffer(heartbeat_seconds=0.01)
    stream = buffer.follow(0)
    try:
        assert await asyncio.wait_for(anext(stream), timeout=1) is None
    finally:
        await stream.aclose()
