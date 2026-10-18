"""core.web_api 的单元测试。

用轻量 fake 替换 ``astrbot.api.web``，直接驱动 handler，不启动 AstrBot。
"""

from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from core.config import get_menu
from core.robot_config import load_menu_config, save_menu_config
from core.state import MenuStateStore
from core.web_api import WebApiBundle, build_status, register_web_apis

MENU: list[dict[str, Any]] = [
    {"type": "menu", "name": "更多"},
    {"type": "send_message", "name": "关于", "message": "/about", "parent": "更多"},
]


@dataclass
class FakeResponse:
    data: Any
    status_code: int = 200


@dataclass
class FakeStream:
    content: Any


class FakeRequest:
    """最小 request 代理：query + async json()。"""

    def __init__(
        self,
        *,
        query: dict[str, str] | None = None,
        payload: Any = None,
    ) -> None:
        self.query = query or {}
        self._payload = payload

    async def json(self, default: Any = None) -> Any:
        return self._payload if self._payload is not None else default


class FakeContext:
    def __init__(self) -> None:
        self.routes: list[tuple[str, Any, list[str], str]] = []

    def register_web_api(
        self,
        route: str,
        handler: Any,
        methods: list[str],
        desc: str,
    ) -> None:
        self.routes.append((route, handler, methods, desc))


class FakeSyncer:
    def __init__(self) -> None:
        self.configs: list[dict[str, Any]] = []
        self.platforms: list[dict[str, str]] = []
        self.calls = 0

    def set_config(self, config: dict[str, Any]) -> None:
        self.configs.append(config)

    def set_platforms(self, platforms: list[dict[str, str]]) -> None:
        self.platforms = platforms

    async def sync_all(self, *, on_progress: Any = None, on_event: Any = None) -> dict[str, Any]:
        self.calls += 1
        if on_event is not None:
            await on_event({"type": "start", "platforms": 1, "items": 1})
        if on_progress is not None:
            await on_progress("reading")
        if on_event is not None:
            await on_event(
                {
                    "type": "platform",
                    "pf_id": "app",
                    "index": 1,
                    "total": 1,
                    "status": "ok",
                    "saved": 1,
                    "action": "updated",
                }
            )
        result = {
            "ok": True,
            "reason": "done",
            "platforms": 1,
            "succeeded": 1,
            "failed": 0,
        }
        if on_event is not None:
            await on_event({"type": "finish", **result})
        return result


def install_web(
    monkeypatch: Any,
    *,
    query: dict[str, str] | None = None,
    payload: Any = None,
) -> types.ModuleType:
    """安装 fake astrbot.api.web，并返回模块以便断言。"""
    web = types.ModuleType("astrbot.api.web")
    web.json_response = lambda data, status_code=200, headers=None: FakeResponse(data, status_code)
    web.error_response = lambda message, status_code=400, data=None, headers=None: FakeResponse(
        {"status": "error", "message": message, "data": data}, status_code
    )
    web.stream_response = lambda content, **kwargs: FakeStream(content)
    web.request = FakeRequest(query=query, payload=payload)

    monkeypatch.setitem(sys.modules, "astrbot.api.web", web)
    astrbot_api = sys.modules.get("astrbot.api")
    if astrbot_api is not None:
        monkeypatch.setattr(astrbot_api, "web", web, raising=False)
    return web


def make_bundle(
    *,
    config: dict[str, Any] | None = None,
    syncer: FakeSyncer | None = None,
    data_dir: Path | None = None,
    save_config: Any = None,
    platforms: list[dict[str, str]] | None = None,
) -> WebApiBundle:
    runtime = (
        platforms
        if platforms is not None
        else [{"appid": "123456789", "secret": "secret-1", "platform": "qq_official"}]
    )
    return WebApiBundle(
        lambda: syncer,
        lambda: config if config is not None else {"menu": MENU},
        get_platforms=lambda: runtime,
        save_config=save_config,
        data_dir=data_dir,
        version="v9.9.9",
    )


def test_build_status_marks_platform_states(tmp_path: Path) -> None:
    config: dict[str, Any] = {
        "sync_menu": True,
        "qq_platforms": [
            {"appid": "123456789", "secret": "s1", "platform": "qq_official"},
            {"appid": "987654321", "secret": "s2", "platform": "qq_official_webhook"},
        ],
        "menu": MENU,
    }
    store = MenuStateStore(tmp_path)
    store.mark_synced("123456789", get_menu(config))
    store.mark_synced("987654321", {"items": []})

    payload = build_status(config, data_dir=tmp_path, version="v9.9.9")

    assert payload["plugin"] == {"name": "astrbot_plugin_qq_custom_menu", "version": "v9.9.9"}
    assert payload["ready"] is True
    assert payload["sync_menu"] is True
    assert payload["state"] == {"available": True}
    assert [item["state"] for item in payload["platforms"]] == ["synced", "pending"]
    assert payload["platforms"][0]["source"] == "compatibility"
    assert payload["platforms"][0]["appid"] == "123****89"
    assert payload["menu"]["top_level"] == 1
    assert payload["menu"]["sub_items"] == 1
    assert payload["menu"]["items"] == get_menu(config)["items"]


def test_build_status_sync_disabled_and_no_state_dir() -> None:
    config: dict[str, Any] = {
        "sync_menu": False,
        "menu": MENU,
    }
    payload = build_status(config, platforms=[], version="v1")
    assert payload["sync_menu"] is False
    assert payload["state"] == {"available": False}
    assert payload["platforms"] == []
    assert payload["ready"] is True


def test_build_status_includes_robot_scenes() -> None:
    config = {"sync_menu": True, "menu": []}
    robot_config = {
        "version": 1,
        "robots": [
            {
                "id": "robot-1",
                "name": "主机器人",
                "appid": "app-robot",
                "secret": "secret",
                "platform": "qq_official",
                "scenes": {
                    "c2c": {
                        "enabled": True,
                        "items": [
                            {
                                "type": "send_message",
                                "name": "帮助",
                                "message": "/help",
                                "parent": "",
                            }
                        ],
                    },
                },
            }
        ],
    }

    payload = build_status(
        config,
        platforms=[],
        robot_config=robot_config,
    )

    platform = payload["platforms"][0]
    assert platform["source"] == "robot"
    assert [scene["scene"] for scene in platform["scenes"]] == ["c2c"]
    assert [scene["state"] for scene in platform["scenes"]] == ["unknown"]
    assert payload["robots"] == {"new": 1, "compatibility": 0}


def test_register_requires_web_module(monkeypatch: Any) -> None:
    monkeypatch.delitem(sys.modules, "astrbot.api.web", raising=False)
    bundle = make_bundle()

    assert bundle.register(FakeContext()) is False


def test_register_requires_context_method(monkeypatch: Any) -> None:
    install_web(monkeypatch)
    bundle = make_bundle()

    class NoRegister:
        pass

    assert bundle.register(NoRegister()) is False


def test_register_adds_all_routes(monkeypatch: Any) -> None:
    install_web(monkeypatch)
    context = FakeContext()

    assert register_web_apis(context, lambda: None, lambda: {}) is not None

    routes = {(route, tuple(methods)) for route, _, methods, _ in context.routes}
    assert routes == {
        ("/astrbot_plugin_qq_custom_menu/status", ("GET",)),
        ("/astrbot_plugin_qq_custom_menu/config", ("GET",)),
        ("/astrbot_plugin_qq_custom_menu/config", ("POST",)),
        ("/astrbot_plugin_qq_custom_menu/robots", ("GET",)),
        ("/astrbot_plugin_qq_custom_menu/robots", ("POST",)),
        ("/astrbot_plugin_qq_custom_menu/robots/import-legacy", ("POST",)),
        ("/astrbot_plugin_qq_custom_menu/sync", ("POST",)),
        ("/astrbot_plugin_qq_custom_menu/sync/events", ("GET",)),
    }


@pytest.mark.asyncio
async def test_page_status_and_config_get(monkeypatch: Any, tmp_path: Path) -> None:
    install_web(monkeypatch)
    syncer = FakeSyncer()
    bundle = make_bundle(config={"menu": MENU, "sync_menu": True}, syncer=syncer, data_dir=tmp_path)

    status = await bundle.page_status()
    assert status.status_code == 200
    assert status.data["ready"] is True
    assert status.data["menu"]["total"] == 2

    config = await bundle.page_config_get()
    assert config.status_code == 200
    assert config.data["plugin"]["version"] == "v9.9.9"
    assert config.data["menu"] == [
        {"type": "menu", "name": "更多", "parent": ""},
        {"type": "send_message", "name": "关于", "parent": "更多", "message": "/about"},
    ]


@pytest.mark.asyncio
async def test_page_config_save_success(monkeypatch: Any) -> None:
    install_web(
        monkeypatch,
        payload={"language": "en-US", "menu": MENU},
    )
    saved: list[dict[str, Any]] = []
    config: dict[str, Any] = {"menu": MENU}

    async def save(values: dict[str, Any]) -> None:
        saved.append(values)
        config.update(values)

    syncer = FakeSyncer()
    bundle = make_bundle(
        config=config,
        syncer=syncer,
        save_config=save,
    )

    response = await bundle.page_config_save()

    assert response.status_code == 200
    assert saved == [
        {
            "language": "en-US",
            "menu": [
                {"__template_key": "menu", "name": "更多"},
                {
                    "__template_key": "send_message",
                    "name": "关于",
                    "message": "/about",
                    "parent": "更多",
                },
            ],
        }
    ]
    assert syncer.configs
    assert response.data["language"] == "en-US"


@pytest.mark.asyncio
async def test_page_config_save_rejects_invalid_body(monkeypatch: Any) -> None:
    install_web(monkeypatch, payload=["not", "an", "object"])
    bundle = make_bundle(save_config=lambda values: None)

    response = await bundle.page_config_save()

    assert response.status_code == 400
    assert "JSON" in response.data["message"]


@pytest.mark.asyncio
async def test_page_config_save_rejects_validation_errors(monkeypatch: Any) -> None:
    install_web(monkeypatch, payload={"menu": [{"type": "bad", "name": "x"}]})
    bundle = make_bundle(save_config=lambda values: None)

    response = await bundle.page_config_save()

    assert response.status_code == 400
    assert response.data["message"]


@pytest.mark.asyncio
async def test_page_config_save_reports_missing_save_callback(monkeypatch: Any) -> None:
    install_web(monkeypatch, payload={})
    bundle = make_bundle()

    response = await bundle.page_config_save()

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_page_config_save_reports_save_failure(monkeypatch: Any) -> None:
    install_web(monkeypatch, payload={"language": "en-US"})

    async def fail(values: dict[str, Any]) -> None:
        raise RuntimeError("disk full")

    bundle = make_bundle(save_config=fail)

    response = await bundle.page_config_save()

    assert response.status_code == 500
    assert "disk full" in response.data["message"]


@pytest.mark.asyncio
async def test_page_sync_start_is_single_flight(monkeypatch: Any) -> None:
    install_web(monkeypatch)
    syncer = FakeSyncer()
    bundle = make_bundle(syncer=syncer)

    first = await bundle.page_sync_start()
    second = await bundle.page_sync_start()

    assert first.data == {"started": True, "busy": False}
    assert second.data == {"started": False, "busy": True}

    await bundle.runner.wait()
    assert syncer.calls == 1


@pytest.mark.asyncio
async def test_sync_handlers_require_syncer(monkeypatch: Any) -> None:
    install_web(monkeypatch)
    bundle = make_bundle(syncer=None)

    assert (await bundle.page_sync_start()).status_code == 503
    assert (await bundle.page_sync_events()).status_code == 503


@pytest.mark.asyncio
async def test_page_sync_events_streams_replayed_events(monkeypatch: Any) -> None:
    install_web(monkeypatch, query={"since": "0"})
    syncer = FakeSyncer()
    bundle = make_bundle(syncer=syncer)

    await bundle.page_sync_start()
    await bundle.runner.wait()
    stream = await bundle.page_sync_events()

    lines = [line async for line in stream.content]
    events = [json.loads(line.removeprefix("data: ").strip()) for line in lines]

    assert [event["type"] for event in events] == ["start", "message", "platform", "finish"]
    assert events[0]["seq"] == 1
    assert events[1]["text"] == "reading"


@pytest.mark.asyncio
async def test_page_sync_events_since_invalid_and_offset(monkeypatch: Any) -> None:
    install_web(monkeypatch, query={"since": "oops"})
    syncer = FakeSyncer()
    bundle = make_bundle(syncer=syncer)
    await bundle.page_sync_start()
    await bundle.runner.wait()

    stream = await bundle.page_sync_events()
    lines = [line async for line in stream.content]
    assert len(lines) == 4

    install_web(monkeypatch, query={"since": "2"})
    stream = await bundle.page_sync_events()
    events = [json.loads(line.removeprefix("data: ").strip()) async for line in stream.content]
    assert events[0]["seq"] == 3


@pytest.mark.asyncio
async def test_make_run_pushes_text_and_structured_events() -> None:
    syncer = FakeSyncer()
    bundle = make_bundle(config={"menu": MENU}, syncer=syncer)
    events: list[dict[str, Any]] = []

    async def emit(event: dict[str, Any]) -> None:
        events.append(event)

    result = await bundle._make_run(syncer)(emit)

    assert result["ok"] is True
    assert syncer.configs == [{"menu": MENU}]
    assert [event["type"] for event in events] == ["start", "message", "platform", "finish"]


@pytest.mark.asyncio
async def test_robot_config_get_and_save(monkeypatch: Any, tmp_path: Path) -> None:
    install_web(
        monkeypatch,
        payload={
            "version": 1,
            "robots": [
                {
                    "id": "",
                    "name": "主机器人",
                    "appid": "app-new",
                    "secret": "secret",
                    "platform": "qq_official",
                    "scenes": {
                        "c2c": {
                            "enabled": True,
                            "items": [
                                {
                                    "type": "send_message",
                                    "name": "帮助",
                                    "message": "/help",
                                    "parent": "",
                                }
                            ],
                        },
                    },
                }
            ],
        },
    )
    bundle = make_bundle(config={}, data_dir=tmp_path)

    empty = await bundle.page_robots_get()
    assert empty.status_code == 200
    assert empty.data["version"] == 1
    assert empty.data["robots"] == []

    saved = await bundle.page_robots_save()
    assert saved.status_code == 200
    assert saved.data["version"] == 2
    assert saved.data["robots"][0]["secret_masked"] == "******"
    assert load_menu_config(tmp_path)["robots"][0]["appid"] == "app-new"


@pytest.mark.asyncio
async def test_robot_config_save_rejects_stale_version(monkeypatch: Any, tmp_path: Path) -> None:
    save_menu_config(tmp_path, {"version": 2, "robots": []})
    install_web(monkeypatch, payload={"version": 1, "robots": []})
    bundle = make_bundle(config={}, data_dir=tmp_path)

    response = await bundle.page_robots_save()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_robot_config_save_requires_version(monkeypatch: Any, tmp_path: Path) -> None:
    install_web(monkeypatch, payload={"robots": []})
    bundle = make_bundle(config={}, data_dir=tmp_path)

    response = await bundle.page_robots_save()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_robot_import_requires_version(monkeypatch: Any, tmp_path: Path) -> None:
    install_web(monkeypatch, payload={"appids": ["123456789"]})
    bundle = make_bundle(config={}, data_dir=tmp_path)

    response = await bundle.page_robots_import_legacy()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_robot_config_imports_legacy_appid(monkeypatch: Any, tmp_path: Path) -> None:
    install_web(
        monkeypatch,
        payload={"version": 1, "appids": ["123456789"]},
    )
    config = {
        "menu": MENU,
        "qq_platforms": [
            {"appid": "123456789", "secret": "legacy-secret", "platform": "qq_official"}
        ],
    }
    bundle = make_bundle(
        config=config,
        data_dir=tmp_path,
        platforms=[{"appid": "123456789", "secret": "legacy-secret", "platform": "qq_official"}],
    )

    response = await bundle.page_robots_import_legacy()

    assert response.status_code == 200
    assert response.data["imported"] == 1
    assert response.data["robots"][0]["appid"] == "123456789"
    assert response.data["robots"][0]["scenes"]["c2c"]["enabled"] is True
