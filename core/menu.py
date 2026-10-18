"""QQ 私聊自定义菜单同步流程。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import aiohttp
from astrbot.api import logger

from .config import SCENE_C2C, mask_appid, menu_from_entries
from .i18n import LOG_TAG, t
from .qq_api import QQClient
from .robot_config import (
    MenuConfigError,
    build_runtime_robots,
    empty_menu_config,
    load_menu_config,
)
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
    """逐机器人同步私聊自定义菜单。"""

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
        self.data_dir = Path(data_dir) if data_dir is not None else None
        self.state = MenuStateStore(data_dir) if data_dir is not None else None

    def set_config(self, config: dict[str, Any]) -> None:
        """Dashboard 保存兼容配置后刷新内存引用。"""
        self.config = config

    def set_platforms(self, platforms: list[dict[str, str]]) -> None:
        """Dashboard 保存兼容凭证后刷新回退平台列表。"""
        self.platforms = platforms

    def _robot_config(self) -> dict[str, Any]:
        if self.data_dir is None:
            return empty_menu_config()
        return load_menu_config(self.data_dir)

    def build_runtime_robots(self) -> list[dict[str, Any]]:
        """读取新版配置并与兼容配置按 AppID 合并。"""
        return build_runtime_robots(
            self.config,
            self._robot_config(),
            self.platforms,
        )

    async def sync(self) -> None:
        """启动同步入口；异常由调用方记录，不影响插件启动。"""
        await self.sync_all()

    async def sync_all(
        self,
        *,
        on_progress: ProgressCallback | None = None,
        on_event: EventCallback | None = None,
    ) -> dict[str, Any]:
        """同步所有已启用的私聊菜单。"""
        try:
            robots = self.build_runtime_robots()
        except MenuConfigError as exc:
            message = t("log.robot_config_load_failed", exc=exc)
            logger.error(f"{LOG_TAG} {message}", exc_info=True)
            await _notify_event(
                on_event,
                {
                    "type": "finish",
                    "ok": False,
                    "reason": "config_error",
                    "platforms": 0,
                    "succeeded": 0,
                    "failed": 0,
                    "error": str(exc),
                },
            )
            raise

        if not robots:
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

        apply = self.config.get("sync_menu", True) is not False
        total = len(robots)
        active_scenes = sum(
            1 for robot in robots if robot["scenes"].get(SCENE_C2C, {}).get("enabled")
        )
        total_items = sum(
            len(robot["scenes"].get(SCENE_C2C, {}).get("items") or [])
            for robot in robots
            if robot["scenes"].get(SCENE_C2C, {}).get("enabled")
        )
        await _notify_event(
            on_event,
            {
                "type": "start",
                "mode": "sync" if apply else "read",
                "platforms": total,
                "scenes": active_scenes,
                "items": total_items,
            },
        )

        succeeded = 0
        failed = 0
        for index, robot in enumerate(robots, start=1):
            appid = str(robot.get("appid") or "")
            display_appid = mask_appid(appid)
            scene = robot["scenes"].get(SCENE_C2C, {})
            scene_result: dict[str, Any]
            try:
                if not scene.get("enabled"):
                    scene_result = {
                        "scene": SCENE_C2C,
                        "status": "ok",
                        "action": "skipped",
                        "saved": 0,
                    }
                else:
                    client = QQClient(appid, str(robot.get("secret") or ""), self.http)
                    target = menu_from_entries(scene.get("items") or [])
                    current = await client.get_menu()
                    remote = current.get("menu")
                    remote = remote if isinstance(remote, dict) else {"items": []}
                    logger.info(
                        t(
                            "log.menu_read_ok",
                            appid=display_appid,
                            menu=remote,
                        )
                    )

                    if not apply:
                        scene_result = {
                            "scene": SCENE_C2C,
                            "status": "ok",
                            "action": "read",
                            "saved": 0,
                        }
                    elif remote == target:
                        if self.state is not None:
                            self.state.mark_scene_synced(appid, SCENE_C2C, target)
                        scene_result = {
                            "scene": SCENE_C2C,
                            "status": "ok",
                            "action": "unchanged",
                            "saved": 0,
                        }
                    else:
                        if not target["items"]:
                            logger.info(t("log.menu_cleared"))
                        await client.update_menu(target)
                        if self.state is not None:
                            self.state.mark_scene_synced(appid, SCENE_C2C, target)
                        scene_result = {
                            "scene": SCENE_C2C,
                            "status": "ok",
                            "action": "updated",
                            "saved": len(target["items"]),
                        }
                succeeded += 1
                message = t(
                    "log.platform_sync_ok",
                    appid=display_appid,
                    scenes=1,
                )
                logger.info(message)
                await _notify_progress(on_progress, message)
            except Exception as exc:
                failed += 1
                scene_result = {
                    "scene": SCENE_C2C,
                    "status": "error",
                    "action": "failed",
                    "saved": 0,
                    "error": str(exc),
                }
                message = t("log.platform_failed", appid=display_appid, exc=exc)
                logger.error(message, exc_info=True)
                await _notify_progress(on_progress, message)

            await _notify_event(
                on_event,
                {
                    "type": "platform",
                    "pf_id": display_appid,
                    "name": str(robot.get("name") or display_appid),
                    "kind": str(robot.get("source") or "robot"),
                    "index": index,
                    "total": total,
                    "status": scene_result["status"],
                    "action": scene_result["action"],
                    "saved": scene_result["saved"],
                    "scenes": [scene_result],
                    **({"error": scene_result["error"]} if scene_result.get("error") else {}),
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
            "scenes": active_scenes,
            "items": total_items,
            "sync_menu": apply,
        }
        await _notify_event(on_event, {"type": "finish", **result})
        return result


__all__ = ["MenuSynchronizer", "ProgressCallback", "EventCallback"]
