"""插件可视化视图（Dashboard）的后端 Web API。

注册的接口（视图内使用相对路径，bridge 会补上插件名前缀）：

- ``GET  /<plugin_name>/status``       状态概览（本地配置 + 同步摘要）
- ``GET  /<plugin_name>/config``       读取可编辑配置（secret 只回掩码）
- ``POST /<plugin_name>/config``       校验并写回配置
- ``POST /<plugin_name>/sync``         触发一次后台同步（单飞）
- ``GET  /<plugin_name>/sync/events``  SSE 推送同步进度
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.api.star import Context

from .config import (
    MENU_LIMITS,
    export_config,
    get_menu,
    get_plugin_platforms,
    mask_appid,
    menu_stats,
    normalize_config_payload,
)
from .i18n import LOG_TAG, t
from .menu import MenuSynchronizer
from .paths import PLUGIN_NAME, PLUGIN_VERSION
from .state import MenuStateStore, menu_digest
from .sync_runner import SyncRunner

STATUS_ROUTE_SUFFIX = "status"
CONFIG_ROUTE_SUFFIX = "config"
SYNC_ROUTE_SUFFIX = "sync"
SYNC_EVENTS_ROUTE_SUFFIX = "sync/events"

SYNC_STATE_SYNCED = "synced"
SYNC_STATE_PENDING = "pending"
SYNC_STATE_UNKNOWN = "unknown"
SYNC_STATE_DISABLED = "disabled"


def _web() -> Any:
    """延迟导入 astrbot.api.web，较早的 AstrBot 版本没有该模块。"""
    from astrbot.api import web

    return web


def _platform_state(
    *,
    sync_menu: bool,
    stored_digest: str | None,
    current_digest: str,
) -> str:
    """根据本地摘要与当前菜单摘要判断单个平台的同步状态。"""
    if not sync_menu:
        return SYNC_STATE_DISABLED
    if stored_digest is None:
        return SYNC_STATE_UNKNOWN
    if stored_digest == current_digest:
        return SYNC_STATE_SYNCED
    return SYNC_STATE_PENDING


def build_status(
    config: dict[str, Any],
    *,
    platforms: list[dict[str, str]] | None = None,
    data_dir: Path | str | None = None,
    version: str = PLUGIN_VERSION,
    ready: bool = True,
) -> dict[str, Any]:
    """组装状态概览响应体（对应前端 ``StatusResponse``）。

    这里只读取本地配置与 ``menu_state.yaml``，不会请求 QQ API，因此可以在每次
    进入页面时安全调用。真实远端状态由同步流程在 PUT 前读取后刷新。
    """
    menu = get_menu(config)
    digest = menu_digest(menu)
    sync_menu = config.get("sync_menu", True) is not False
    runtime = get_plugin_platforms(config) if platforms is None else platforms

    stored: dict[str, str] = {}
    if data_dir is not None:
        stored = MenuStateStore(data_dir).load()

    source = "plugin" if get_plugin_platforms(config) else "astrbot"
    platform_payload = [
        {
            "pf_id": mask_appid(entry.get("appid")),
            "appid": mask_appid(entry.get("appid")),
            "platform": str(entry.get("platform") or "qq_official"),
            "secret_set": bool(entry.get("secret")),
            "source": source,
            "state": _platform_state(
                sync_menu=sync_menu,
                stored_digest=stored.get(str(entry.get("appid") or "")),
                current_digest=digest,
            ),
        }
        for entry in runtime
    ]

    return {
        "plugin": {"name": PLUGIN_NAME, "version": version},
        "ready": ready,
        "sync_menu": sync_menu,
        "platforms": platform_payload,
        "menu": {
            **menu_stats(config),
            "digest": digest,
            "items": menu["items"],
        },
        "state": {"available": data_dir is not None},
    }


class WebApiBundle:
    """Dashboard Web API 的 handler 集合，以及共享的同步任务状态。"""

    def __init__(
        self,
        get_syncer: Callable[[], MenuSynchronizer | None],
        get_config: Callable[[], dict[str, Any]],
        *,
        get_platforms: Callable[[], list[dict[str, str]]] | None = None,
        save_config: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        data_dir: Path | str | None = None,
        version: str = PLUGIN_VERSION,
    ) -> None:
        self._get_syncer = get_syncer
        self._get_config = get_config
        self._get_platforms = get_platforms
        self._save_config = save_config
        self._data_dir = Path(data_dir) if data_dir is not None else None
        self._version = version
        self.runner = SyncRunner()

    def _platforms(self) -> list[dict[str, str]]:
        return self._get_platforms() if self._get_platforms is not None else []

    def _status_payload(self) -> dict[str, Any]:
        return build_status(
            self._get_config(),
            platforms=self._platforms(),
            data_dir=self._data_dir,
            version=self._version,
            ready=self._get_syncer() is not None,
        )

    def _config_payload(self) -> dict[str, Any]:
        payload = export_config(self._get_config(), self._platforms())
        payload["plugin"] = {"name": PLUGIN_NAME, "version": self._version}
        return payload

    # ------------------------------------------------------------------
    # 注册
    # ------------------------------------------------------------------

    def register(self, context: Context) -> bool:
        """注册全部视图接口，宿主不支持时返回 False。"""
        try:
            from astrbot.api import web  # noqa: F401
        except Exception as exc:  # pragma: no cover - 依赖宿主版本
            logger.warning(f"{LOG_TAG} " + t("web.api_unavailable", exc=exc))
            return False

        if not callable(getattr(context, "register_web_api", None)):
            logger.warning(
                f"{LOG_TAG} " + t("web.api_unavailable", exc="context.register_web_api missing")
            )
            return False

        prefix = f"/{PLUGIN_NAME}"
        context.register_web_api(
            f"{prefix}/{STATUS_ROUTE_SUFFIX}",
            self.page_status,
            ["GET"],
            "Plugin dashboard status overview",
        )
        context.register_web_api(
            f"{prefix}/{CONFIG_ROUTE_SUFFIX}",
            self.page_config_get,
            ["GET"],
            "Plugin dashboard config read",
        )
        context.register_web_api(
            f"{prefix}/{CONFIG_ROUTE_SUFFIX}",
            self.page_config_save,
            ["POST"],
            "Plugin dashboard config save",
        )
        context.register_web_api(
            f"{prefix}/{SYNC_ROUTE_SUFFIX}",
            self.page_sync_start,
            ["POST"],
            "Plugin dashboard menu sync",
        )
        context.register_web_api(
            f"{prefix}/{SYNC_EVENTS_ROUTE_SUFFIX}",
            self.page_sync_events,
            ["GET"],
            "Plugin dashboard menu sync progress (SSE)",
        )
        return True

    # ------------------------------------------------------------------
    # handler
    # ------------------------------------------------------------------

    async def page_status(self) -> Any:
        web = _web()
        return web.json_response(self._status_payload())

    async def page_config_get(self) -> Any:
        web = _web()
        return web.json_response(self._config_payload())

    async def page_config_save(self) -> Any:
        web = _web()
        if self._save_config is None:
            return web.error_response(t("web.config_unavailable"), status_code=503)

        payload = await web.request.json(default={})
        if not isinstance(payload, dict):
            return web.error_response(t("web.config_invalid_body"), status_code=400)

        values, errors = normalize_config_payload(self._get_config(), payload)
        if errors:
            return web.error_response(t("common.error_separator").join(errors), status_code=400)

        try:
            await self._save_config(values)
        except Exception as exc:
            logger.error(f"{LOG_TAG} " + t("web.config_save_failed", exc=exc), exc_info=True)
            return web.error_response(t("web.config_save_failed", exc=exc), status_code=500)

        syncer = self._get_syncer()
        if syncer is not None:
            syncer.set_config(self._get_config())
        return web.json_response(self._config_payload())

    async def page_sync_start(self) -> Any:
        web = _web()
        syncer = self._get_syncer()
        if syncer is None:
            return web.error_response(t("web.not_ready"), status_code=503)
        started = self.runner.start(self._make_run(syncer))
        return web.json_response({"started": started, "busy": not started})

    async def page_sync_events(self) -> Any:
        web = _web()
        if self._get_syncer() is None:
            return web.error_response(t("web.not_ready"), status_code=503)

        raw_since = web.request.query.get("since", "")
        try:
            since = max(0, int(raw_since))
        except (TypeError, ValueError):
            since = 0

        async def events():  # noqa: ANN202 - 流式响应体由宿主消费
            async for event in self.runner.stream(since):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        return web.stream_response(events())

    def _make_run(
        self,
        syncer: MenuSynchronizer,
    ) -> Callable[[Callable[[dict[str, Any]], Awaitable[None]]], Awaitable[Any]]:
        """构造同步任务：先刷新配置，再把文本进度与结构化事件一起推送。"""

        async def run(emit: Callable[[dict[str, Any]], Awaitable[None]]) -> Any:
            syncer.set_config(self._get_config())

            async def push_text(message: str) -> None:
                await emit({"type": "message", "text": message})

            return await syncer.sync_all(on_progress=push_text, on_event=emit)

        return run


def register_web_apis(
    context: Context,
    get_syncer: Callable[[], MenuSynchronizer | None],
    get_config: Callable[[], dict[str, Any]],
    *,
    get_platforms: Callable[[], list[dict[str, str]]] | None = None,
    save_config: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    data_dir: Path | str | None = None,
    version: str = PLUGIN_VERSION,
) -> WebApiBundle | None:
    """注册 Dashboard Web API，宿主不支持时返回 None。"""
    bundle = WebApiBundle(
        get_syncer,
        get_config,
        get_platforms=get_platforms,
        save_config=save_config,
        data_dir=data_dir,
        version=version,
    )
    if not bundle.register(context):
        return None
    return bundle


__all__ = [
    "CONFIG_ROUTE_SUFFIX",
    "MENU_LIMITS",
    "STATUS_ROUTE_SUFFIX",
    "SYNC_EVENTS_ROUTE_SUFFIX",
    "SYNC_ROUTE_SUFFIX",
    "SYNC_STATE_DISABLED",
    "SYNC_STATE_PENDING",
    "SYNC_STATE_SYNCED",
    "SYNC_STATE_UNKNOWN",
    "WebApiBundle",
    "build_status",
    "register_web_apis",
]
