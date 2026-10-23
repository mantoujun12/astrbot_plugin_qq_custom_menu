"""AstrBot QQ 官方机器人自定义菜单插件入口。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiohttp
from astrbot.api import logger
from astrbot.api.star import Context, Star, register

from .core import (
    LOG_TAG,
    PLUGIN_NAME,
    PLUGIN_VERSION,
    LogBuffer,
    MenuSynchronizer,
    get_platforms,
    initialize_i18n,
    migrate_menu_config,
    register_web_apis,
    resolve_plugin_data_dir,
    t,
)


@register(
    PLUGIN_NAME,
    "mantoujun12",
    "用户在 AstrBot WebUI 配置 QQ 官方机器人私聊自定义菜单",
    PLUGIN_VERSION,
    "https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu",
)
class QQCustomMenuPlugin(Star):
    """启动时将配置的菜单同步到 QQ 官方机器人。"""

    def __init__(self, context: Context, config):
        super().__init__(context)
        initialize_i18n(Path(__file__).resolve().parent / "core" / "i18n", config.get("language"))
        self._log_buffer: LogBuffer | None = LogBuffer()
        self._web_api = None
        try:
            self._log_buffer.install(getattr(self, "logger", None) or logger)
        except Exception as exc:
            # 日志页属于可选能力；宿主 logger 不兼容时不能阻止插件启动。
            self._close_log_buffer()
            logger.warning(
                "%s %s",
                LOG_TAG,
                t("log.log_capture_unavailable", exc=exc),
            )
        try:
            # 旧版菜单为 dict 结构，首次加载时迁移为 template_list 并保存
            migrate_menu_config(config)
        except Exception as exc:
            logger.warning(
                "%s %s",
                LOG_TAG,
                t("log.migration_failed", exc=exc),
                exc_info=True,
            )
        try:
            # 保留 AstrBotConfig 原对象，Dashboard 保存配置时才能调用它的持久化方法
            self.config = config
            self.data_dir = resolve_plugin_data_dir(self.context)
            self._http: aiohttp.ClientSession | None = None
            self._syncer: MenuSynchronizer | None = None
            # 视图接口在 __init__ 注册；syncer 到 initialize() 才创建，handler
            # 每次请求都会通过回调取最新实例，避免持有过期引用
            self._web_api = register_web_apis(
                self.context,
                lambda: self._syncer,
                lambda: dict(self.config),
                get_platforms=lambda: get_platforms(self.config),
                save_config=self._save_config,
                data_dir=self.data_dir,
                log_buffer=self._log_buffer,
                version=PLUGIN_VERSION,
            )
        except Exception:
            self._close_log_buffer()
            raise

    def _close_log_buffer(self) -> None:
        """关闭日志缓冲并确保重复或失败启动时都可安全调用。"""
        buffer = self._log_buffer
        self._log_buffer = None
        if buffer is not None:
            try:
                buffer.close()
            except Exception as exc:
                logger.debug(
                    "%s %s",
                    LOG_TAG,
                    t("log.log_cleanup_failed", exc=exc),
                )

    async def _save_config(self, values: dict[str, Any]) -> None:
        """把 Dashboard 提交的字段写回 AstrBot 配置并刷新同步器。"""
        save_async = getattr(self.config, "save_config_async", None)
        if callable(save_async):
            await save_async(values)
        else:
            self.config.update(values)
            save_sync = getattr(self.config, "save_config", None)
            if callable(save_sync):
                save_sync()
        # save_config_async 内部只在写入时合并字段，这里再同步一次内存视图
        self.config.update(values)
        if self._syncer is not None:
            self._syncer.set_config(self.config)
            self._syncer.set_platforms(get_platforms(self.config))

    async def initialize(self) -> None:
        self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        self._syncer = MenuSynchronizer(
            self._http,
            get_platforms(self.config),
            self.config,
            self.data_dir,
        )
        try:
            await self._syncer.sync()
        except Exception as exc:
            logger.error("%s %s", LOG_TAG, t("log.sync_failed", exc=exc), exc_info=True)

    async def terminate(self) -> None:
        if self._web_api is not None:
            await self._web_api.runner.close()
            self._web_api = None
        if self._http is not None and not self._http.closed:
            await self._http.close()
        self._http = None
        self._syncer = None
        self._close_log_buffer()


__all__ = ["QQCustomMenuPlugin"]
