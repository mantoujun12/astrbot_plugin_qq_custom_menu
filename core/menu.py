"""QQ 自定义菜单同步流程。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiohttp
from astrbot.api import logger

from .config import get_menu
from .i18n import t
from .qq_api import QQClient
from .state import MenuStateStore


class MenuSynchronizer:
    def __init__(
        self,
        http: aiohttp.ClientSession,
        platforms: list[dict[str, str]],
        config: dict[str, Any],
        data_dir: Path | str | None = None,
    ):
        self.http = http
        self.platforms = platforms
        self.config = config
        self.state = MenuStateStore(data_dir) if data_dir is not None else None

    async def sync(self) -> None:
        if not self.platforms:
            logger.warning(t("log.no_platforms"))
            return
        menu = get_menu(self.config)
        sync_menu = self.config.get("sync_menu", True)
        if sync_menu and not menu["items"]:
            # PUT 会整表覆盖远程菜单，菜单项为空时同步会清空 QQ 上已有的自定义菜单
            logger.info(t("log.menu_cleared"))
        for platform in self.platforms:
            client = QQClient(platform["appid"], platform["secret"], self.http)
            current = await client.get_menu()
            logger.info(
                t(
                    "log.menu_read_ok",
                    appid=platform["appid"],
                    menu=current.get("menu"),
                )
            )
            if sync_menu:
                appid = platform["appid"]
                if self.state is not None and self.state.is_unchanged(appid, menu):
                    logger.info(t("log.menu_unchanged", appid=appid))
                    continue
                await client.update_menu(menu)
                if self.state is not None:
                    self.state.mark_synced(appid, menu)
                logger.info(t("log.menu_sync_ok", appid=appid))