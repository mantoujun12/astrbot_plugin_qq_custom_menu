"""core.qq_api.QQClient 的单元测试 (注入 FakeSession, 无真实网络)"""

from __future__ import annotations

from typing import Any

import pytest

from core.qq_api import API_BASE, TOKEN_URL, QQClient
from tests.fakes import FakeSession


def make_client(session: FakeSession) -> QQClient:
    return QQClient(appid="app1", secret="sec1", http=session)


def token_calls(session: FakeSession) -> list[dict[str, Any]]:
    return [r for r in session.requests if r["url"] == TOKEN_URL]


# ---------------------------------------------------------------------------
# access_token 获取与缓存
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_fetched_once_and_cached() -> None:
    session = FakeSession()
    session.route_token({"access_token": "tok1", "expires_in": 7200})
    session.route_menu("GET", "/v2/menu", payload={"menu": {"items": []}})
    client = make_client(session)

    await client.get_menu()
    await client.get_menu()

    # 两次读取菜单只换取一次 token
    assert len(token_calls(session)) == 1


@pytest.mark.asyncio
async def test_token_refetched_after_expiry() -> None:
    session = FakeSession()
    session.route_token({"access_token": "tok1", "expires_in": 7200})
    session.route_menu("GET", "/v2/menu", payload={"menu": {"items": []}})
    client = make_client(session)

    await client.get_menu()
    # 模拟过期: 把过期时间拨回过去
    client._expires_at = 0.0
    await client.get_menu()

    assert len(token_calls(session)) == 2


@pytest.mark.asyncio
async def test_token_http_error_raises() -> None:
    session = FakeSession()
    session.route_token({"message": "bad"}, status=500)
    client = make_client(session)

    with pytest.raises(RuntimeError, match="500"):
        await client.get_menu()


@pytest.mark.asyncio
async def test_token_missing_in_response_raises() -> None:
    session = FakeSession()
    session.route_token({"expires_in": 7200})  # 无 access_token
    client = make_client(session)

    with pytest.raises(RuntimeError, match="access_token"):
        await client.get_menu()


# ---------------------------------------------------------------------------
# request: 鉴权头 / 错误处理 / 响应归一化
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_sends_auth_header_and_base_url() -> None:
    session = FakeSession()
    session.route_token({"access_token": "tok9", "expires_in": 7200})
    session.route_menu("GET", "/v2/menu", payload={"menu": {"items": []}})
    client = make_client(session)

    await client.get_menu()

    call = [r for r in session.requests if r["url"].startswith(API_BASE)][0]
    assert call["method"] == "GET"
    assert call["url"] == f"{API_BASE}/v2/menu"
    assert call["kwargs"]["headers"]["Authorization"] == "QQBot tok9"


@pytest.mark.asyncio
async def test_request_http_error_raises_runtime_error() -> None:
    session = FakeSession()
    session.route_token({"access_token": "tok1", "expires_in": 7200})
    session.route_menu("GET", "/v2/menu", status=400, payload={"code": 40030008})
    client = make_client(session)

    with pytest.raises(RuntimeError, match="400"):
        await client.get_menu()


@pytest.mark.asyncio
async def test_request_non_dict_json_wrapped_as_data() -> None:
    session = FakeSession()
    session.route_token({"access_token": "tok1", "expires_in": 7200})
    session.route_menu("GET", "/v2/menu", payload=[1, 2, 3])  # type: ignore[arg-type]
    client = make_client(session)

    assert await client.get_menu() == {"data": [1, 2, 3]}


# ---------------------------------------------------------------------------
# get_menu / update_menu
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_menu_wraps_body_in_menu_key() -> None:
    session = FakeSession()
    session.route_token({"access_token": "tok1", "expires_in": 7200})
    session.route_menu("PUT", "/v2/menu", payload={})
    client = make_client(session)

    menu = {"items": [{"type": "send_message", "name": "帮助", "send_message": "/help"}]}
    await client.update_menu(menu)

    last = session.requests[-1]
    assert last["method"] == "PUT"
    assert last["url"] == f"{API_BASE}/v2/menu"
    assert last["kwargs"]["json"] == {"menu": menu}
