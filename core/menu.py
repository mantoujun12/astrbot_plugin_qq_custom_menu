"""QQ 自定义菜单同步流程。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import aiohttp
from astrbot.api import logger

from .config import get_menu, mask_appid
from .i18n import t
from .qq_api import QQClient
from .state import MenuStateStore

ProgressCallback = Callable[[str], Awaitable[None]]
EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


async def _notify_progress(callback: ProgressCallback | None, message: str) -> None:
    if callback is not None:
        await callback(message)


async def _notify_event(callback: EventCallback | None, event: dict[str, Any]) -> None:
    if callback is not None:
        await callback(event)


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

    def set_config(self, config: dict[str, Any]) -> None:
        """Dashboard 保存配置后调用，让下一次同步读取最新内容。"""
        self.config = config

    def set_platforms(self, platforms: list[dict[str, str]]) -> None:
        """Dashboard 保存凭证后调用，让下一次同步使用最新平台列表。"""
        self.platforms = platforms

    async def sync(self) -> None:
        """启动时同步入口：保留原有行为，失败只记录日志。"""
        await self.sync_all()

    async def sync_all(
        self,
        *,
        on_progress: ProgressCallback | None = None,
        on_event: EventCallback | None = None,
    ) -> dict[str, Any]:
        """同步所有平台，并通过回调推送文本进度与结构化事件。

        单个平台失败不会中止其余平台；返回值与 finish 事件中的统计一致。
        """
        total = len(self.platforms)
        if not self.platforms:
            message = t("log.no_platforms")
            logger.warning(message)
            await _notify_progress(on_progress, message)
            result = {
                "ok": True,
                "reason": "no_platforms",
                "platforms": 0,
                "succeeded": 0,
                "failed": 0,
            }
            await _notify_event(on_event, {"type": "finish", **result})
            return result

        menu = get_menu(self.config)
        sync_menu = self.config.get("sync_menu", True) is not False
        if sync_menu and not menu["items"]:
            # PUT 会整表覆盖远程菜单，菜单项为空时同步会清空 QQ 上已有的自定义菜单
            message = t("log.menu_cleared")
            logger.info(message)
            await _notify_progress(on_progress, message)

        await _notify_event(
            on_event,
            {
                "type": "start",
                "mode": "sync" if sync_menu else "read",
                "platforms": total,
                "items": len(menu["items"]),
            },
        )

        succeeded = 0
        failed = 0
        for index, platform in enumerate(self.platforms, start=1):
            appid = platform["appid"]
            display_appid = mask_appid(appid)
            try:
                client = QQClient(appid, platform["secret"], self.http)
                current = await client.get_menu()
                read_message = t(
                    "log.menu_read_ok",
                    appid=display_appid,
                    menu=current.get("menu"),
                )
                logger.info(read_message)
                await _notify_progress(on_progress, read_message)

                if not sync_menu:
                    result: dict[str, Any] = {
                        "status": "ok",
                        "action": "read",
                        "saved": 0,
                    }
                else:
                    # 是否 PUT 必须以刚读取到的远端菜单为准：本地摘要可能已过期，
                    # 也可能在 PUT 成功后保存失败，不能单独用于跳过同步。
                    remote_menu = current.get("menu")
                    if remote_menu == menu:
                        if self.state is not None:
                            # 远端已与配置一致，用远端内容修复可能过期的本地摘要。
                            self.state.mark_synced(appid, remote_menu)
                        message = t("log.menu_unchanged", appid=display_appid)
                        logger.info(message)
                        await _notify_progress(on_progress, message)
                        result = {"status": "ok", "action": "unchanged", "saved": 0}
                    else:
                        await client.update_menu(menu)
                        if self.state is not None:
                            self.state.mark_synced(appid, menu)
                        message = t("log.menu_sync_ok", appid=display_appid)
                        logger.info(message)
                        await _notify_progress(on_progress, message)
                        result = {
                            "status": "ok",
                            "action": "updated",
                            "saved": len(menu["items"]),
                        }
                succeeded += 1
            except Exception as exc:
                failed += 1
                message = t("log.platform_failed", appid=display_appid, exc=exc)
                logger.error(message, exc_info=True)
                await _notify_progress(on_progress, message)
                result = {"status": "error", "action": "failed", "saved": 0, "error": str(exc)}

            await _notify_event(
                on_event,
                {
                    "type": "platform",
                    "pf_id": display_appid,
                    "index": index,
                    "total": total,
                    **result,
                },
            )

        summary = t("log.sync_summary", succeeded=succeeded, failed=failed)
        logger.info(summary)
        await _notify_progress(on_progress, summary)
        result = {
            "ok": failed == 0,
            "reason": "done",
            "platforms": total,
            "succeeded": succeeded,
            "failed": failed,
            "items": len(menu["items"]),
            "sync_menu": sync_menu,
        }
        await _notify_event(on_event, {"type": "finish", **result})
        return result


__all__ = ["MenuSynchronizer", "ProgressCallback", "EventCallback"]
