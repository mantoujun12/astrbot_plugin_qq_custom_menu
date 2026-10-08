"""AstrBot QQ 官方机器人自定义菜单插件入口。"""

from __future__ import annotations

from pathlib import Path

import aiohttp
from astrbot.api import logger
from astrbot.api.star import Context, Star, register

from .core import MenuSynchronizer, get_platforms, migrate_menu_config


@register(
    "astrbot_plugin_qq_custom_menu",
    "mantoujun12",
    "用户在 AstrBot WebUI 配置 QQ 官方机器人私聊自定义菜单",
    "v0.1.0",
    "https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu",
)
class QQCustomMenuPlugin(Star):
    """启动时将配置的菜单同步到 QQ 官方机器人。"""

    def __init__(self, context: Context, config):
        super().__init__(context)
        try:
            # 旧版菜单为 dict 结构，首次加载时迁移为 template_list 并保存
            migrate_menu_config(config)
        except Exception as exc:
            logger.warning("菜单配置迁移失败: %s", exc, exc_info=True)
        self.config = dict(config)
        self._http: aiohttp.ClientSession | None = None
        self._syncer: MenuSynchronizer | None = None

    async def initialize(self) -> None:
        self._http = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        )
        self._syncer = MenuSynchronizer(
            self._http,
            get_platforms(self.config, self.context),
            self.config,
        )
        try:
            await self._syncer.sync()
        except Exception as exc:
            logger.error("QQ 自定义菜单同步失败: %s", exc, exc_info=True)

    async def terminate(self) -> None:
        if self._http is not None and not self._http.closed:
            await self._http.close()
        self._http = None
        self._syncer = None


__all__ = ["QQCustomMenuPlugin"]
