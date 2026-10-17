"""core.menu.MenuSynchronizer 的单元测试 (注入 FakeSession, 无真实网络)"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import pytest

from core.config import mask_appid
from core.menu import MenuSynchronizer
from core.qq_api import API_BASE
from tests.fakes import FakeSession

MENU_STATE_DATA = Path(__file__).resolve().parent / "_menu_state_data"


@pytest.fixture(autouse=True)
def cleanup_menu_state_data() -> None:
    yield
    if MENU_STATE_DATA.exists():
        shutil.rmtree(MENU_STATE_DATA)


PLATFORM: dict[str, str] = {"appid": "app1", "secret": "sec1", "platform": "qq_official"}


def menu_calls(session: FakeSession, method: str) -> list[dict[str, Any]]:
    url = f"{API_BASE}/v2/menu"
    return [r for r in session.requests if r["method"] == method and r["url"] == url]


def make_session() -> FakeSession:
    session = FakeSession()
    session.route_token({"access_token": "tok1", "expires_in": 7200})
    session.route_menu("GET", "/v2/menu", payload={"menu": {"items": []}})
    session.route_menu("PUT", "/v2/menu", payload={})
    return session


@pytest.mark.asyncio
async def test_sync_without_platforms_skips(caplog: Any) -> None:
    session = make_session()
    syncer = MenuSynchronizer(session, [], {})

    await syncer.sync()

    assert session.requests == []
    assert "跳过" in caplog.text


@pytest.mark.asyncio
async def test_sync_reads_then_overwrites_when_enabled() -> None:
    session = make_session()
    config: dict[str, Any] = {
        "sync_menu": True,
        "menu": [{"type": "send_message", "name": "帮助", "send_message": "/help"}],
    }
    syncer = MenuSynchronizer(session, [PLATFORM], config)

    await syncer.sync()

    assert len(menu_calls(session, "GET")) == 1
    put = menu_calls(session, "PUT")
    assert len(put) == 1
    assert put[0]["kwargs"]["json"] == {
        "menu": {"items": [{"type": "send_message", "name": "帮助", "send_message": "/help"}]}
    }


@pytest.mark.asyncio
async def test_sync_defaults_to_enabled_when_key_missing() -> None:
    session = make_session()
    syncer = MenuSynchronizer(
        session,
        [PLATFORM],
        {"menu": [{"type": "send_message", "name": "帮助", "send_message": "/help"}]},
    )

    await syncer.sync()

    assert len(menu_calls(session, "PUT")) == 1


@pytest.mark.asyncio
async def test_sync_disabled_only_reads(caplog: Any) -> None:
    session = make_session()
    syncer = MenuSynchronizer(
        session,
        [PLATFORM],
        {"sync_menu": False, "menu": [{"type": "send_message", "name": "x", "send_message": "/x"}]},
    )

    await syncer.sync()

    assert len(menu_calls(session, "GET")) == 1
    assert menu_calls(session, "PUT") == []


@pytest.mark.asyncio
async def test_sync_empty_menu_clears_remote(caplog: Any) -> None:
    session = make_session()
    # 远端仍有旧菜单，配置为空时才需要 PUT 清空。
    session.route_menu(
        "GET",
        "/v2/menu",
        payload={"menu": {"items": [{"type": "link", "name": "旧", "link": "https://old"}]}},
    )
    syncer = MenuSynchronizer(session, [PLATFORM], {"sync_menu": True, "menu": []})

    with caplog.at_level(logging.INFO, logger="astrbot"):
        await syncer.sync()

    put = menu_calls(session, "PUT")
    assert len(put) == 1
    assert put[0]["kwargs"]["json"] == {"menu": {"items": []}}
    assert "清空" in caplog.text


@pytest.mark.asyncio
async def test_sync_iterates_every_platform() -> None:
    session = make_session()
    platforms: list[dict[str, str]] = [
        {"appid": "app1", "secret": "s1", "platform": "qq_official"},
        {"appid": "app2", "secret": "s2", "platform": "qq_official_webhook"},
    ]
    syncer = MenuSynchronizer(
        session,
        platforms,
        {"sync_menu": True, "menu": [{"type": "send_message", "name": "x", "send_message": "/x"}]},
    )

    await syncer.sync()

    # 每个平台一份独立凭证: 各自的 GET + PUT, token 也各取一次
    assert len(menu_calls(session, "GET")) == 2
    assert len(menu_calls(session, "PUT")) == 2
    token_requests = [r for r in session.requests if "getAppAccessToken" in r["url"]]
    assert len(token_requests) == 2
    appids = {r["kwargs"]["json"]["appId"] for r in token_requests}
    assert appids == {"app1", "app2"}


def make_state_dir() -> Path:
    data_dir = MENU_STATE_DATA
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True)
    return data_dir


@pytest.mark.asyncio
async def test_sync_skips_when_remote_matches_config() -> None:
    session = make_session()
    menu = {"items": [{"type": "send_message", "name": "帮助", "send_message": "/help"}]}
    config: dict[str, Any] = {"sync_menu": True, "menu": menu["items"]}
    # 远端已经是目标菜单：不应再 PUT，但仍要刷新本地摘要。
    session.route_menu("GET", "/v2/menu", payload={"menu": menu})
    data_dir = make_state_dir()
    syncer = MenuSynchronizer(session, [PLATFORM], config, data_dir)

    await syncer.sync()

    assert menu_calls(session, "PUT") == []
    assert syncer.state is not None
    assert syncer.state.is_unchanged(PLATFORM["appid"], menu) is True


@pytest.mark.asyncio
async def test_sync_puts_when_remote_differs_from_config_even_if_state_matches() -> None:
    session = make_session()
    menu = {"items": [{"type": "send_message", "name": "帮助", "send_message": "/help"}]}
    config: dict[str, Any] = {"sync_menu": True, "menu": menu["items"]}
    data_dir = make_state_dir()
    syncer = MenuSynchronizer(session, [PLATFORM], config, data_dir)
    assert syncer.state is not None
    # 本地摘要声称已同步，但远端内容不同：仍必须 PUT。
    syncer.state.mark_synced(PLATFORM["appid"], menu)

    await syncer.sync()

    assert len(menu_calls(session, "PUT")) == 1


@pytest.mark.asyncio
async def test_sync_does_not_trust_stale_state_after_remote_reset() -> None:
    session = make_session()
    menu = {"items": [{"type": "send_message", "name": "帮助", "send_message": "/help"}]}
    config: dict[str, Any] = {"sync_menu": True, "menu": menu["items"]}
    # 模拟远端被重置为空、但本地摘要仍为已同步状态。
    session.route_menu("GET", "/v2/menu", payload={"menu": {"items": []}})
    data_dir = make_state_dir()
    syncer = MenuSynchronizer(session, [PLATFORM], config, data_dir)
    assert syncer.state is not None
    syncer.state.mark_synced(PLATFORM["appid"], menu)

    await syncer.sync()

    assert len(menu_calls(session, "PUT")) == 1


@pytest.mark.asyncio
async def test_sync_all_emits_structured_events() -> None:
    session = make_session()
    config: dict[str, Any] = {
        "sync_menu": True,
        "menu": [{"type": "send_message", "name": "帮助", "send_message": "/help"}],
    }
    syncer = MenuSynchronizer(session, [PLATFORM], config)
    events: list[dict[str, Any]] = []
    messages: list[str] = []

    result = await syncer.sync_all(
        on_progress=lambda message: _collect(messages, message),
        on_event=lambda event: _collect(events, event),
    )

    assert result == {
        "ok": True,
        "reason": "done",
        "platforms": 1,
        "succeeded": 1,
        "failed": 0,
        "items": 1,
        "sync_menu": True,
    }
    assert [event["type"] for event in events] == ["start", "platform", "finish"]
    assert events[0]["mode"] == "sync"
    assert events[1]["action"] == "updated"
    assert events[1]["pf_id"] == mask_appid(PLATFORM["appid"])
    assert messages


async def _collect(target: list[Any], value: Any) -> None:
    target.append(value)


@pytest.mark.asyncio
async def test_sync_all_without_platforms_emits_finish(caplog: Any) -> None:
    session = make_session()
    syncer = MenuSynchronizer(session, [], {})
    events: list[dict[str, Any]] = []

    result = await syncer.sync_all(on_event=lambda event: _collect(events, event))

    assert result["reason"] == "no_platforms"
    assert events == [
        {
            "type": "finish",
            "ok": True,
            "reason": "no_platforms",
            "platforms": 0,
            "succeeded": 0,
            "failed": 0,
        }
    ]
    assert session.requests == []
    assert "跳过" in caplog.text


@pytest.mark.asyncio
async def test_sync_all_disabled_only_reads() -> None:
    session = make_session()
    syncer = MenuSynchronizer(
        session,
        [PLATFORM],
        {"sync_menu": False, "menu": [{"type": "send_message", "name": "x", "send_message": "/x"}]},
    )
    events: list[dict[str, Any]] = []

    result = await syncer.sync_all(on_event=lambda event: _collect(events, event))

    assert result["ok"] is True
    assert events[0]["mode"] == "read"
    assert events[1]["action"] == "read"
    assert menu_calls(session, "PUT") == []


@pytest.mark.asyncio
async def test_sync_all_continues_after_platform_failure(monkeypatch: Any) -> None:
    class FakeClient:
        def __init__(self, appid: str, secret: str, http: Any) -> None:
            self.appid = appid

        async def get_menu(self) -> dict[str, Any]:
            if self.appid == "bad":
                raise RuntimeError("boom")
            return {"menu": {"items": []}}

        async def update_menu(self, menu: dict[str, Any]) -> dict[str, Any]:
            return {}

    monkeypatch.setattr("core.menu.QQClient", FakeClient)
    platforms = [
        {"appid": "good", "secret": "s1", "platform": "qq_official"},
        {"appid": "bad", "secret": "s2", "platform": "qq_official"},
    ]
    syncer = MenuSynchronizer(
        FakeSession(),
        platforms,
        {"sync_menu": True, "menu": [{"type": "send_message", "name": "x", "send_message": "/x"}]},
    )
    events: list[dict[str, Any]] = []
    messages: list[str] = []

    result = await syncer.sync_all(
        on_progress=lambda message: _collect(messages, message),
        on_event=lambda event: _collect(events, event),
    )

    assert result["ok"] is False
    assert result["succeeded"] == 1
    assert result["failed"] == 1
    platform_events = [event for event in events if event["type"] == "platform"]
    assert [event["status"] for event in platform_events] == ["ok", "error"]
    assert "boom" in platform_events[1]["error"]
    assert any("boom" in message for message in messages)


def test_set_config_and_platforms() -> None:
    syncer = MenuSynchronizer(FakeSession(), [PLATFORM], {"menu": []})
    syncer.set_config({"sync_menu": False})
    syncer.set_platforms([])

    assert syncer.config == {"sync_menu": False}
    assert syncer.platforms == []
