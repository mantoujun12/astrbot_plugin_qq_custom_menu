"""测试通用假件 (fakes): FakeResponse / FakeSession / FakeContext

只实现被测代码实际调用的方法, 未实现的方法调用会直接 AttributeError,
避免 fakes 默默偏离真实接口。
"""

from __future__ import annotations

from typing import Any

from core.qq_api import API_BASE, TOKEN_URL


class FakeResponse:
    """假 aiohttp.Response: 预置 status / json / text"""

    def __init__(
        self,
        *,
        status: int = 200,
        payload: dict[str, Any] | None = None,
        text: str = "",
        json_error: Exception | None = None,
    ) -> None:
        self.status = status
        self._payload = payload if payload is not None else {}
        self._text = text
        self._json_error = json_error

    async def json(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if self._json_error is not None:
            raise self._json_error
        return self._payload

    async def text(self) -> str:
        return self._text

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None


class FakeSession:
    """假 aiohttp.ClientSession: 按 (method, url) 路由返回预置响应

    - 记录所有请求 (method, url, kwargs), 供断言
    - 未匹配到路由时返回 500 + {"raw": ...}, 不抛异常,
      与真实 aiohttp 行为对齐 (HTTP 错误也是正常响应)
    """

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.routes: dict[tuple[str, str], FakeResponse] = {}

    def route(self, method: str, url: str, response: FakeResponse) -> None:
        self.routes[(method.upper(), url)] = response

    def _match(self, method: str, url: str) -> FakeResponse:
        return self.routes.get(
            (method.upper(), url),
            FakeResponse(status=500, payload={"raw": "no route"}, text="no route"),
        )

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        """与真实 aiohttp 对齐: 同步返回 async context manager, 由调用方 `async with`"""
        self.requests.append({"method": method, "url": url, "kwargs": kwargs})
        return self._match(method, url)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        """与真实 aiohttp 对齐: 同步返回 async context manager, 由调用方 `async with`"""
        self.requests.append({"method": "POST", "url": url, "kwargs": kwargs})
        return self._match("POST", url)

    def closed(self) -> bool:
        return False

    # ---- 便捷构造器: QQ 菜单 API 路由 ----

    def route_token(self, payload: dict[str, Any], status: int = 200) -> None:
        self.route("POST", TOKEN_URL, FakeResponse(status=status, payload=payload))

    def route_menu(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        status: int = 200,
        text: str = "",
        json_error: Exception | None = None,
    ) -> None:
        self.route(
            method,
            f"{API_BASE}{path}",
            FakeResponse(status=status, payload=payload, text=text, json_error=json_error),
        )


class FakeContext:
    """假 AstrBot Context: get_platforms 回退路径只需 get_config()"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config if config is not None else {}

    def get_config(self) -> dict[str, Any]:
        return self._config


__all__ = ["API_BASE", "TOKEN_URL", "FakeContext", "FakeResponse", "FakeSession"]
