"""QQ 官方机器人菜单 API 客户端。"""

from __future__ import annotations

import time
from typing import Any

import aiohttp

from .i18n import t

TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"  # noqa: S105 - 端点 URL, 非密钥
API_BASE = "https://api.bot.qq.com"


class QQClient:
    def __init__(self, appid: str, secret: str, http: aiohttp.ClientSession):
        self.appid = appid
        self.secret = secret
        self.http = http
        self._token: str | None = None
        self._expires_at = 0.0

    async def _token_value(self) -> str:
        if self._token and self._expires_at > time.time():
            return self._token
        async with self.http.post(
            TOKEN_URL,
            json={"appId": self.appid, "clientSecret": self.secret},
        ) as response:
            data = await response.json()
            if response.status >= 400 or not data.get("access_token"):
                raise RuntimeError(t("log.token_failed", status=response.status, data=data))
        self._token = str(data["access_token"])
        self._expires_at = time.time() + max(int(data.get("expires_in", 7200)) - 600, 60)
        return self._token

    async def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = await self._token_value()
        async with self.http.request(
            method,
            f"{API_BASE}{path}",
            headers={"Authorization": f"QQBot {token}"},
            json=body,
        ) as response:
            try:
                data = await response.json(content_type=None)
            except Exception:
                data = {"raw": await response.text()}
            if response.status >= 400:
                raise RuntimeError(
                    t(
                        "log.api_failed",
                        method=method,
                        path=path,
                        status=response.status,
                        data=data,
                    )
                )
            return data if isinstance(data, dict) else {"data": data}

    async def get_menu(self) -> dict[str, Any]:
        return await self.request("GET", "/v2/menu")

    async def update_menu(self, menu: dict[str, Any]) -> dict[str, Any]:
        return await self.request("PUT", "/v2/menu", {"menu": menu})
