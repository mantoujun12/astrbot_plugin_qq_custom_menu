"""QQ 自定义菜单同步流程。"""

from __future__ import annotations

from typing import Any

import aiohttp
from astrbot.api import logger

from .config import get_menu
from .qq_api import QQClient


class MenuSynchronizer:
    def __init__(
        self,
        http: aiohttp.ClientSession,
        platforms: list[dict[str, str]],
        config: dict[str, Any],
    ):
        self.http = http
        self.platforms = platforms
        self.config = config

    async def sync(self) -> None:
        if not self.platforms:
            logger.warning("未配置 QQ 官方机器人凭证，跳过自定义菜单同步")
            return
        menu = get_menu(self.config)
        for platform in self.platforms:
            client = QQClient(platform["appid"], platform["secret"], self.http)
            current = await client.get_menu()
            logger.info("QQ 菜单读取成功: appid=%s, menu=%s", platform["appid"], current.get("menu"))
            if self.config.get("sync_menu", True):
                await client.update_menu(menu)
                logger.info("QQ 菜单同步成功: appid=%s", platform["appid"])
