"""main.py 装配层测试。

main.py 使用包内相对导入（``from .core import ...``），仓库根目录本身不是包，
因此这里用 :mod:`importlib` 把它挂到一个临时包命名空间下再加载。
AstrBot 依赖由 ``tests/conftest.py`` 注入的 stub 提供。
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "astrbot_plugin_qq_custom_menu"


class FakeConfig(dict):
    """可记录 save_config 调用的 dict，模拟 AstrBotConfig。"""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        super().__init__(data or {})
        self.saved = 0

    def save_config(self) -> None:
        self.saved += 1


class FakeContext:
    """最小 AstrBot Context：提供 get_config()。"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    def get_config(self) -> dict[str, Any]:
        return self._config


class FakeSession:
    """最小 aiohttp.ClientSession：只记录 close()。"""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def load_main() -> types.ModuleType:
    """把仓库根挂成包并加载 main.py，返回模块对象（进程内复用）。"""
    package = sys.modules.get(PACKAGE)
    if package is None:
        package = types.ModuleType(PACKAGE)
        package.__path__ = [str(ROOT)]  # type: ignore[attr-defined]
        sys.modules[PACKAGE] = package

    module_name = f"{PACKAGE}.main"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, ROOT / "main.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_init_runs_migration(monkeypatch: Any) -> None:
    main = load_main()
    migrated: list[dict[str, Any]] = []
    monkeypatch.setattr(
        main,
        "migrate_menu_config",
        lambda config: migrated.append(config) or True,
    )
    config = FakeConfig({"language": "en-US"})

    plugin = main.QQCustomMenuPlugin(FakeContext(), config)

    assert migrated == [config]
    assert plugin.config == dict(config)
    assert plugin._http is None
    assert plugin._syncer is None


def test_init_logs_migration_failure(monkeypatch: Any, caplog: Any) -> None:
    main = load_main()

    def fail_migration(config: Any) -> bool:
        raise RuntimeError("migration boom")

    monkeypatch.setattr(main, "migrate_menu_config", fail_migration)
    with caplog.at_level("WARNING", logger="astrbot"):
        main.QQCustomMenuPlugin(FakeContext(), FakeConfig())

    assert "migration boom" in caplog.text


@pytest.mark.asyncio
async def test_initialize_syncs_and_terminate_closes(monkeypatch: Any, tmp_path: Path) -> None:
    main = load_main()
    sessions: list[FakeSession] = []
    syncers: list[Any] = []

    class Syncer:
        def __init__(self, http: Any, platforms: Any, config: Any, data_dir: Any) -> None:
            self.http = http
            self.platforms = platforms
            self.config = config
            self.data_dir = data_dir
            self.synced = False
            syncers.append(self)

        async def sync(self) -> None:
            self.synced = True

    def make_session(**kwargs: Any) -> FakeSession:
        session = FakeSession(**kwargs)
        sessions.append(session)
        return session

    monkeypatch.setattr(main.aiohttp, "ClientSession", make_session)
    monkeypatch.setattr(main, "MenuSynchronizer", Syncer)
    monkeypatch.setattr(main, "resolve_plugin_data_dir", lambda context: tmp_path)

    plugin = main.QQCustomMenuPlugin(
        FakeContext(
            {
                "platform": [
                    {
                        "type": "qq_official",
                        "appid": "astrbot-only",
                        "secret": "should-not-be-used",
                    }
                ]
            }
        ),
        FakeConfig({"language": "zh-CN"}),
    )
    await plugin.initialize()

    assert len(syncers) == 1
    assert syncers[0].synced is True
    assert syncers[0].platforms == []
    assert syncers[0].data_dir == tmp_path
    assert plugin._http is sessions[0]
    assert sessions[0].kwargs["timeout"].total == 15

    await plugin.terminate()

    assert sessions[0].closed is True
    assert plugin._http is None
    assert plugin._syncer is None


@pytest.mark.asyncio
async def test_initialize_logs_sync_failure(monkeypatch: Any, tmp_path: Path, caplog: Any) -> None:
    main = load_main()

    class FailingSyncer:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def sync(self) -> None:
            raise RuntimeError("sync boom")

    monkeypatch.setattr(main.aiohttp, "ClientSession", lambda **kwargs: FakeSession(**kwargs))
    monkeypatch.setattr(main, "MenuSynchronizer", FailingSyncer)
    monkeypatch.setattr(main, "resolve_plugin_data_dir", lambda context: tmp_path)

    plugin = main.QQCustomMenuPlugin(FakeContext(), FakeConfig())
    with caplog.at_level("ERROR", logger="astrbot"):
        await plugin.initialize()

    assert "sync boom" in caplog.text
    await plugin.terminate()


@pytest.mark.asyncio
async def test_terminate_without_initialize_is_noop() -> None:
    main = load_main()
    plugin = main.QQCustomMenuPlugin(FakeContext(), FakeConfig())

    await plugin.terminate()

    assert plugin._http is None
    assert plugin._syncer is None


@pytest.mark.asyncio
async def test_terminate_skips_already_closed_session() -> None:
    main = load_main()
    plugin = main.QQCustomMenuPlugin(FakeContext(), FakeConfig())
    session = FakeSession()
    session.closed = True
    plugin._http = session

    await plugin.terminate()

    assert plugin._http is None


class FakeMenuSyncer:
    def __init__(self) -> None:
        self.configs: list[Any] = []
        self.platforms: list[Any] = []

    def set_config(self, config: Any) -> None:
        self.configs.append(config)

    def set_platforms(self, platforms: Any) -> None:
        self.platforms.append(platforms)


class AsyncSaveConfig(FakeConfig):
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        super().__init__(data)
        self.async_saved: list[Any] = []

    async def save_config_async(self, values: dict[str, Any] | None = None) -> None:
        self.async_saved.append(values)
        if values:
            self.update(values)


@pytest.mark.asyncio
async def test_save_config_prefers_async_api(monkeypatch: Any, tmp_path: Path) -> None:
    main = load_main()
    monkeypatch.setattr(main, "resolve_plugin_data_dir", lambda context: tmp_path)
    config = AsyncSaveConfig()
    plugin = main.QQCustomMenuPlugin(FakeContext(), config)
    syncer = FakeMenuSyncer()
    plugin._syncer = syncer

    await plugin._save_config({"language": "en-US"})

    assert config.async_saved == [{"language": "en-US"}]
    assert config["language"] == "en-US"
    assert syncer.configs == [config]
    assert syncer.platforms == [[]]


@pytest.mark.asyncio
async def test_save_config_falls_back_to_sync_api(monkeypatch: Any, tmp_path: Path) -> None:
    main = load_main()
    monkeypatch.setattr(main, "resolve_plugin_data_dir", lambda context: tmp_path)
    config = FakeConfig()
    plugin = main.QQCustomMenuPlugin(FakeContext(), config)

    await plugin._save_config({"sync_menu": False})

    assert config.saved == 1
    assert config["sync_menu"] is False


@pytest.mark.asyncio
async def test_save_config_plain_dict(monkeypatch: Any, tmp_path: Path) -> None:
    main = load_main()
    monkeypatch.setattr(main, "resolve_plugin_data_dir", lambda context: tmp_path)
    config: dict[str, Any] = {}
    plugin = main.QQCustomMenuPlugin(FakeContext(), config)

    await plugin._save_config({"language": "en-US"})

    assert config["language"] == "en-US"


@pytest.mark.asyncio
async def test_terminate_closes_web_api(monkeypatch: Any, tmp_path: Path) -> None:
    main = load_main()

    class Runner:
        def __init__(self) -> None:
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    class Bundle:
        def __init__(self) -> None:
            self.runner = Runner()

    bundle = Bundle()
    monkeypatch.setattr(main, "register_web_apis", lambda *args, **kwargs: bundle)
    monkeypatch.setattr(main, "resolve_plugin_data_dir", lambda context: tmp_path)

    plugin = main.QQCustomMenuPlugin(FakeContext(), FakeConfig())
    await plugin.terminate()

    assert bundle.runner.closed is True
    assert plugin._web_api is None
