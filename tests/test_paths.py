"""core.paths.resolve_plugin_data_dir 的单元测试。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from core.paths import resolve_plugin_data_dir

TEST_ROOT = Path(__file__).resolve().parent / "_paths_data"


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


class ContextWithGetter:
    def __init__(self, path: Path) -> None:
        self.path = path

    def get_data_dir(self, plugin_name: str) -> Path:
        return self.path / plugin_name


class ContextWithAttr:
    def __init__(self, path: Path) -> None:
        self.data_dir = path


def test_context_getter_creates_and_returns_dir() -> None:
    tmp_path = make_test_dir("context-getter")
    context = ContextWithGetter(tmp_path)
    resolved = resolve_plugin_data_dir(context, "demo")
    assert resolved == tmp_path / "demo"
    assert resolved.is_dir()


def test_context_data_dir_attr_fallback() -> None:
    tmp_path = make_test_dir("context-attr")
    resolved = resolve_plugin_data_dir(ContextWithAttr(tmp_path), "demo")
    assert resolved == tmp_path / "plugin_data" / "demo"
    assert resolved.is_dir()


def test_env_astrbot_root_fallback(monkeypatch: Any) -> None:
    tmp_path = make_test_dir("env-root")
    monkeypatch.setenv("ASTRBOT_ROOT", str(tmp_path))
    resolved = resolve_plugin_data_dir(None, "demo")
    assert resolved == tmp_path / "data" / "plugin_data" / "demo"
    assert resolved.is_dir()


def test_context_getter_precedes_env(monkeypatch: Any) -> None:
    monkeypatch.setenv("ASTRBOT_ROOT", str(make_test_dir("env-loser")))
    context_path = make_test_dir("context-winner")
    resolved = resolve_plugin_data_dir(ContextWithGetter(context_path), "demo")
    assert resolved == context_path / "demo"


def test_star_tools_precedes_context(monkeypatch: Any) -> None:
    class StarTools:
        @staticmethod
        def get_data_dir(plugin_name: str) -> Path:
            return make_test_dir("star-tools") / plugin_name

    monkeypatch.setattr(
        "core.paths._star_tools_data_dir",
        lambda plugin_name: StarTools.get_data_dir(plugin_name),
    )
    resolved = resolve_plugin_data_dir(ContextWithGetter(make_test_dir("context-loser")), "demo")
    assert resolved.name == "demo"
    assert "star-tools" in resolved.parts


def test_home_fallback(monkeypatch: Any) -> None:
    home = make_test_dir("home")
    monkeypatch.delenv("ASTRBOT_ROOT", raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr("core.paths.Path.home", lambda: home)

    resolved = resolve_plugin_data_dir(None, "demo")

    assert resolved == home / ".astrbot" / "data" / "plugin_data" / "demo"
    assert resolved.is_dir()


def test_never_writes_into_working_directory(monkeypatch: Any) -> None:
    probe = make_test_dir("cwd-probe")
    monkeypatch.delenv("ASTRBOT_ROOT", raising=False)

    def fail_home() -> Path:
        raise RuntimeError("no home")

    monkeypatch.setattr("core.paths.Path.home", fail_home)
    monkeypatch.setattr("core.paths.Path.cwd", lambda: probe)
    with pytest.raises(RuntimeError):
        resolve_plugin_data_dir(None, "demo")
    assert not (probe / "data" / "plugin_data" / "demo").exists()


def test_call_or_none_handles_exception() -> None:
    from core.paths import _call_or_none

    assert _call_or_none(lambda: (_ for _ in ()).throw(RuntimeError("boom"))) is None


def test_unwritable_first_candidate_falls_back(monkeypatch: Any) -> None:
    first = make_test_dir("unwritable")
    second = make_test_dir("fallback")

    monkeypatch.setattr("core.paths._star_tools_data_dir", lambda plugin_name: None)
    monkeypatch.setattr(
        "core.paths._iter_candidates",
        lambda context, plugin_name: iter([first / "bad", second / plugin_name]),
    )

    real_mkdir = Path.mkdir

    def flaky_mkdir(self: Path, *args: Any, **kwargs: Any) -> None:
        if "bad" in self.parts:
            raise OSError("unwritable")
        real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", flaky_mkdir)
    assert resolve_plugin_data_dir(None, "demo") == second / "demo"
