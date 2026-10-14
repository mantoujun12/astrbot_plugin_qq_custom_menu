"""core.state.MenuStateStore 的单元测试。"""

from __future__ import annotations

import shutil
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


def test_save_failure_is_logged(monkeypatch: Any) -> None:
    tmp_path = make_test_dir("save-failure")
    store = MenuStateStore(tmp_path)

    def fail_safe_dump(*args: Any, **kwargs: Any) -> None:
        raise OSError("boom")

    monkeypatch.setattr("core.state.yaml.safe_dump", fail_safe_dump)
    store.save({"app1": "digest"})


def test_tmp_cleanup_after_save_failure(monkeypatch: Any) -> None:
    tmp_path = make_test_dir("tmp-cleanup")
    store = MenuStateStore(tmp_path)
    tmp_file = store.state_file.with_suffix(".yaml.tmp")
    tmp_file.write_text("leftover", encoding="utf-8")

    def fail_replace(*args: Any, **kwargs: Any) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", fail_replace)
    store.save({"app1": "digest"})
    assert not tmp_file.exists()
