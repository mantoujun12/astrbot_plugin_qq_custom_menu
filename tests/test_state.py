"""core.state.MenuStateStore 的单元测试。"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest

from core.state import STATE_FILENAME, MenuStateStore, menu_digest

TEST_ROOT = Path(__file__).resolve().parent / "_state_data"


@pytest.fixture(autouse=True)
def cleanup_test_data() -> None:
    yield
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)


def make_test_dir(name: str) -> Path:
    path = TEST_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_save_and_load_roundtrip() -> None:
    tmp_path = make_test_dir("roundtrip")
    store = MenuStateStore(tmp_path)
    menu = {"items": [{"type": "send_message", "name": "帮助", "send_message": "/help"}]}
    digest = menu_digest(menu)
    store.save({"app1": digest})
    assert store.load() == {"app1": digest}
    assert (tmp_path / STATE_FILENAME).exists()


def test_missing_file_returns_empty() -> None:
    tmp_path = make_test_dir("missing")
    assert MenuStateStore(tmp_path).load() == {}


def test_corrupt_file_returns_empty() -> None:
    tmp_path = make_test_dir("corrupt")
    (tmp_path / STATE_FILENAME).write_text("{not valid yaml: [[", encoding="utf-8")
    assert MenuStateStore(tmp_path).load() == {}


def test_is_unchanged_and_mark_synced() -> None:
    tmp_path = make_test_dir("unchanged")
    store = MenuStateStore(tmp_path)
    menu = {"items": []}
    assert store.is_unchanged("app1", menu) is False
    store.mark_synced("app1", menu)
    assert store.is_unchanged("app1", menu) is True
    assert (
        store.is_unchanged("app1", {"items": [{"type": "link", "name": "x", "link": "https://x"}]})
        is False
    )


def test_non_mapping_state_returns_empty() -> None:
    tmp_path = make_test_dir("non-mapping")
    (tmp_path / STATE_FILENAME).write_text("- item\n", encoding="utf-8")
    assert MenuStateStore(tmp_path).load() == {}


def test_save_failure_is_logged(monkeypatch: Any, caplog: Any) -> None:
    tmp_path = make_test_dir("save-failure")
    store = MenuStateStore(tmp_path)

    def fail_safe_dump(*args: Any, **kwargs: Any) -> None:
        raise OSError("boom")

    monkeypatch.setattr("core.state.yaml.safe_dump", fail_safe_dump)
    with caplog.at_level("WARNING", logger="astrbot"):
        store.save({"app1": "digest"})

    assert "save menu state failed" in caplog.text
    assert "boom" in caplog.text


def test_tmp_cleanup_after_save_failure(monkeypatch: Any) -> None:
    tmp_path = make_test_dir("tmp-cleanup")
    store = MenuStateStore(tmp_path)
    tmp_file = store.state_file.with_suffix(".yaml.tmp")
    tmp_file.write_text("leftover", encoding="utf-8")

    def fail_replace(*args: Any, **kwargs: Any) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("core.state.os.replace", fail_replace)
    store.save({"app1": "digest"})
    assert not any(tmp_path.glob(f"{STATE_FILENAME}.*.tmp"))


def test_mark_synced_does_not_clobber_other_appids() -> None:
    tmp_path = make_test_dir("concurrent")
    first = MenuStateStore(tmp_path)
    second = MenuStateStore(tmp_path)

    first.mark_synced("app1", {"items": []})
    second.mark_synced("app2", {"items": []})

    state = first.load()
    assert set(state) == {"app1", "app2"}


def test_scene_digest_keeps_c2c_compatibility_alias() -> None:
    tmp_path = make_test_dir("scenes")
    store = MenuStateStore(tmp_path)
    c2c = {"items": [{"type": "send_message", "name": "帮助", "send_message": "/help"}]}

    store.mark_scene_synced("app1", "c2c", c2c)

    assert store.digest_for_scene("app1", "c2c") == menu_digest(c2c)
    assert store.load()["app1"] == menu_digest(c2c)


def test_write_uses_unique_tmp_files(monkeypatch: Any) -> None:
    tmp_path = make_test_dir("unique-tmp")
    store = MenuStateStore(tmp_path)
    seen: list[str] = []

    real_mkstemp = tempfile.mkstemp

    def record_mkstemp(*args: Any, **kwargs: Any) -> tuple[int, str]:
        fd, name = real_mkstemp(*args, **kwargs)
        seen.append(name)
        return fd, name

    monkeypatch.setattr("core.state.tempfile.mkstemp", record_mkstemp)
    store.mark_synced("app1", {"items": []})
    store.mark_synced("app2", {"items": []})

    assert len(seen) == 2
    assert seen[0] != seen[1]


def test_stale_lock_is_removed_and_write_succeeds() -> None:
    import os
    import time

    tmp_path = make_test_dir("stale-lock")
    store = MenuStateStore(tmp_path)
    store.lock_file.write_text("stale", encoding="utf-8")
    old = time.time() - 3600
    os.utime(store.lock_file, (old, old))

    store.mark_synced("app1", {"items": []})

    assert store.is_unchanged("app1", {"items": []}) is True
    assert not store.lock_file.exists()


def test_lock_timeout_writes_without_lock(monkeypatch: Any, caplog: Any) -> None:
    tmp_path = make_test_dir("lock-timeout")
    store = MenuStateStore(tmp_path)
    store.lock_file.write_text("held", encoding="utf-8")
    monkeypatch.setattr("core.state.LOCK_TIMEOUT_SECONDS", 0.0)

    with caplog.at_level("WARNING", logger="astrbot"):
        store.mark_synced("app1", {"items": []})

    assert "state lock unavailable" in caplog.text
    assert store.is_unchanged("app1", {"items": []}) is True


def test_lock_release_failure_is_tolerated(monkeypatch: Any) -> None:
    tmp_path = make_test_dir("lock-release")
    store = MenuStateStore(tmp_path)
    real_unlink = Path.unlink

    def flaky_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
        if self == store.lock_file:
            raise OSError("cannot release")
        real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    store.mark_synced("app1", {"items": []})

    assert store.is_unchanged("app1", {"items": []}) is True


def test_lock_acquire_oserror_is_logged(monkeypatch: Any, caplog: Any) -> None:
    tmp_path = make_test_dir("lock-oserror")
    store = MenuStateStore(tmp_path)

    def fail_open(*args: Any, **kwargs: Any) -> int:
        raise OSError("cannot open lock")

    monkeypatch.setattr("core.state.os.open", fail_open)
    with caplog.at_level("WARNING", logger="astrbot"):
        store.mark_synced("app1", {"items": []})

    assert "acquire state lock failed" in caplog.text


def test_state_save_close_failure_is_tolerated(monkeypatch: Any) -> None:
    tmp_path = make_test_dir("close-failure")
    store = MenuStateStore(tmp_path)
    real_fdopen = os.fdopen

    def flaky_fdopen(*args: Any, **kwargs: Any) -> Any:
        handle = real_fdopen(*args, **kwargs)
        real_close = handle.close

        def close_and_fail() -> None:
            real_close()
            raise OSError("close failed")

        handle.close = close_and_fail
        return handle

    monkeypatch.setattr("core.state.os.fdopen", flaky_fdopen)
    store.mark_synced("app1", {"items": []})


def test_stale_lock_stat_failure_falls_back(monkeypatch: Any) -> None:
    tmp_path = make_test_dir("stale-lock-stat")
    store = MenuStateStore(tmp_path)
    store.lock_file.write_text("held", encoding="utf-8")
    monkeypatch.setattr("core.state.LOCK_TIMEOUT_SECONDS", 0.06)

    real_stat = Path.stat

    def flaky_stat(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == store.lock_file:
            raise OSError("stat failed")
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", flaky_stat)
    store.mark_synced("app1", {"items": []})

    assert store.is_unchanged("app1", {"items": []}) is True


def test_stale_lock_unlink_failure_is_logged(monkeypatch: Any, caplog: Any) -> None:
    import time

    tmp_path = make_test_dir("stale-lock-unlink")
    store = MenuStateStore(tmp_path)
    store.lock_file.write_text("stale", encoding="utf-8")
    old = time.time() - 3600
    os.utime(store.lock_file, (old, old))
    monkeypatch.setattr("core.state.LOCK_TIMEOUT_SECONDS", 0.02)

    real_unlink = Path.unlink

    def flaky_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
        if self == store.lock_file:
            raise OSError("unlink failed")
        real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    with caplog.at_level("DEBUG", logger="astrbot"):
        store.mark_synced("app1", {"items": []})

    assert "remove stale state lock failed" in caplog.text
    assert store.is_unchanged("app1", {"items": []}) is True


def test_release_lock_file_already_gone() -> None:
    tmp_path = make_test_dir("lock-gone")
    store = MenuStateStore(tmp_path)

    with store._locked():
        store.lock_file.unlink()

    assert not store.lock_file.exists()


def test_cleanup_tmp_failure_is_tolerated(monkeypatch: Any, caplog: Any) -> None:
    tmp_path = make_test_dir("tmp-cleanup-failure")
    store = MenuStateStore(tmp_path)

    def fail_replace(*args: Any, **kwargs: Any) -> None:
        raise OSError("replace failed")

    real_unlink = Path.unlink

    def flaky_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
        if self.name.endswith(".tmp"):
            raise OSError("cleanup failed")
        real_unlink(self, *args, **kwargs)

    monkeypatch.setattr("core.state.os.replace", fail_replace)
    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    with caplog.at_level("DEBUG", logger="astrbot"):
        store.save({"app1": "digest"})

    assert "cleanup menu state tmp failed" in caplog.text
