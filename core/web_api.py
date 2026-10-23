"""插件可视化视图（Dashboard）的 Web API。

除状态、配置与同步接口外，``GET /<plugin_name>/logs/events`` 通过 SSE
回放最近 1000 条插件日志，并持续推送新记录。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.api.star import Context

from .config import (
    MENU_LIMITS,
    SCENE_C2C,
    export_config,
    get_menu,
    get_plugin_platforms,
    mask_appid,
    menu_from_entries,
    menu_stats,
    normalize_config_payload,
)
from .i18n import LOG_TAG, t
from .log_stream import LogBuffer, LogSubscriberLimitError
from .menu import MenuSynchronizer
from .paths import PLUGIN_NAME, PLUGIN_VERSION
from .robot_config import (
    MenuConfigError,
    build_runtime_robots,
    empty_menu_config,
    export_menu_config,
    legacy_to_robot_drafts,
    load_menu_config,
    robot_item_counts,
    save_menu_config,
    validate_menu_config,
)
from .state import MenuStateStore, menu_digest
from .sync_runner import SyncRunner

STATUS_ROUTE_SUFFIX = "status"
CONFIG_ROUTE_SUFFIX = "config"
ROBOTS_ROUTE_SUFFIX = "robots"
ROBOTS_IMPORT_ROUTE_SUFFIX = "robots/import-legacy"
SYNC_ROUTE_SUFFIX = "sync"
SYNC_EVENTS_ROUTE_SUFFIX = "sync/events"
LOG_EVENTS_ROUTE_SUFFIX = "logs/events"

SYNC_STATE_SYNCED = "synced"
SYNC_STATE_PENDING = "pending"
SYNC_STATE_UNKNOWN = "unknown"
SYNC_STATE_DISABLED = "disabled"


def _web() -> Any:
    """延迟导入 astrbot.api.web，兼容较早的 AstrBot 版本。"""
    from astrbot.api import web

    return web


def _platform_state(
    *,
    sync_menu: bool,
    stored_digest: str | None,
    current_digest: str,
) -> str:
    if not sync_menu:
        return SYNC_STATE_DISABLED
    if stored_digest is None:
        return SYNC_STATE_UNKNOWN
    if stored_digest == current_digest:
        return SYNC_STATE_SYNCED
    return SYNC_STATE_PENDING


def _aggregate_state(states: list[str]) -> str:
    if not states:
        return SYNC_STATE_DISABLED
    if SYNC_STATE_DISABLED in states and all(state == SYNC_STATE_DISABLED for state in states):
        return SYNC_STATE_DISABLED
    active = [state for state in states if state != SYNC_STATE_DISABLED]
    if not active:
        return SYNC_STATE_DISABLED
    if SYNC_STATE_PENDING in active:
        return SYNC_STATE_PENDING
    if SYNC_STATE_UNKNOWN in active:
        return SYNC_STATE_UNKNOWN
    return SYNC_STATE_SYNCED


def _scene_status(
    scene: str,
    scene_config: dict[str, Any],
    *,
    sync_menu: bool,
    appid: str,
    store: MenuStateStore | None,
) -> dict[str, Any]:
    enabled = bool(scene_config.get("enabled", False))
    items = scene_config.get("items") if isinstance(scene_config.get("items"), list) else []
    digest = menu_digest(menu_from_entries(items))
    stored = store.digest_for_scene(appid, scene) if store is not None and enabled else None
    state = (
        _platform_state(
            sync_menu=sync_menu,
            stored_digest=stored,
            current_digest=digest,
        )
        if enabled
        else SYNC_STATE_DISABLED
    )
    return {
        "scene": scene,
        "enabled": enabled,
        "state": state,
        "item_count": len(items),
        "digest": digest,
    }


def _load_robot_config_for_status(
    data_dir: Path | str | None,
) -> dict[str, Any]:
    if data_dir is None:
        return empty_menu_config()
    return load_menu_config(data_dir)


def build_status(
    config: dict[str, Any],
    *,
    platforms: list[dict[str, str]] | None = None,
    data_dir: Path | str | None = None,
    robot_config: dict[str, Any] | None = None,
    version: str = PLUGIN_VERSION,
    ready: bool = True,
) -> dict[str, Any]:
    """组装本地状态概览，不请求 QQ API。"""
    runtime_platforms = get_plugin_platforms(config) if platforms is None else platforms
    robot_config = _load_robot_config_for_status(data_dir) if robot_config is None else robot_config
    runtime = build_runtime_robots(config, robot_config, runtime_platforms)
    store = MenuStateStore(data_dir) if data_dir is not None else None
    sync_menu = config.get("sync_menu", True) is not False
    platform_payload: list[dict[str, Any]] = []
    for robot in runtime:
        appid = str(robot.get("appid") or "")
        scenes_config = robot.get("scenes") if isinstance(robot.get("scenes"), dict) else {}
        scenes = [
            _scene_status(
                scene,
                scenes_config.get(scene, {}) if isinstance(scenes_config, dict) else {},
                sync_menu=sync_menu,
                appid=appid,
                store=store,
            )
            for scene in (SCENE_C2C,)
        ]
        active_states = [str(scene["state"]) for scene in scenes if scene["enabled"]]
        platform_payload.append(
            {
                "pf_id": mask_appid(appid),
                "appid": mask_appid(appid),
                "name": str(robot.get("name") or mask_appid(appid)),
                "platform": str(robot.get("platform") or "qq_official"),
                "secret_set": bool(robot.get("secret")),
                "source": str(robot.get("source") or "robot"),
                "state": _aggregate_state(active_states),
                "scenes": scenes,
            }
        )

    counts = robot_item_counts(robot_config)
    has_new_config = bool(robot_config.get("robots"))
    if has_new_config:
        menu_payload = {
            "top_level": counts["c2c_top_level"],
            "sub_items": counts["c2c_sub_items"],
            "total": counts["c2c_items"],
            "top_level_max": MENU_LIMITS["top_level_max"],
            "sub_items_max": MENU_LIMITS["sub_items_max"],
            "digest": menu_digest(
                {
                    "robots": [
                        {
                            "appid": robot.get("appid"),
                            "scenes": robot.get("scenes"),
                        }
                        for robot in runtime
                    ]
                }
            ),
            "items": [],
        }
    else:
        legacy_menu = get_menu(config)
        menu_payload = {
            **menu_stats(config),
            "digest": menu_digest(legacy_menu),
            "items": legacy_menu["items"],
        }

    return {
        "plugin": {"name": PLUGIN_NAME, "version": version},
        "ready": ready,
        "sync_menu": sync_menu,
        "platforms": platform_payload,
        "menu": menu_payload,
        "robots": {
            "new": counts["robots"],
            "compatibility": sum(1 for robot in runtime if robot.get("source") == "compatibility"),
        },
        "state": {"available": data_dir is not None},
    }


class WebApiBundle:
    """Dashboard Web API 的 handler 集合与共享同步任务状态。"""

    def __init__(
        self,
        get_syncer: Callable[[], MenuSynchronizer | None],
        get_config: Callable[[], dict[str, Any]],
        *,
        get_platforms: Callable[[], list[dict[str, str]]] | None = None,
        save_config: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        data_dir: Path | str | None = None,
        log_buffer: LogBuffer | None = None,
        version: str = PLUGIN_VERSION,
    ) -> None:
        self._get_syncer = get_syncer
        self._get_config = get_config
        self._get_platforms = get_platforms
        self._save_config = save_config
        self._data_dir = Path(data_dir) if data_dir is not None else None
        self._log_buffer = log_buffer
        self._version = version
        self._config_lock = asyncio.Lock()
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

    def _load_robot_config(self) -> dict[str, Any]:
        if self._data_dir is None:
            return empty_menu_config()
        return load_menu_config(self._data_dir)

    def _robot_response(self) -> dict[str, Any]:
        payload = export_menu_config(self._load_robot_config())
        payload["plugin"] = {"name": PLUGIN_NAME, "version": self._version}
        return payload

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
        routes = (
            (
                f"{prefix}/{STATUS_ROUTE_SUFFIX}",
                self.page_status,
                ["GET"],
                "Plugin dashboard status overview",
            ),
            (
                f"{prefix}/{CONFIG_ROUTE_SUFFIX}",
                self.page_config_get,
                ["GET"],
                "Plugin compatibility config read",
            ),
            (
                f"{prefix}/{CONFIG_ROUTE_SUFFIX}",
                self.page_config_save,
                ["POST"],
                "Plugin compatibility config save",
            ),
            (
                f"{prefix}/{ROBOTS_ROUTE_SUFFIX}",
                self.page_robots_get,
                ["GET"],
                "Plugin robot menu config read",
            ),
            (
                f"{prefix}/{ROBOTS_ROUTE_SUFFIX}",
                self.page_robots_save,
                ["POST"],
                "Plugin robot menu config save",
            ),
            (
                f"{prefix}/{ROBOTS_IMPORT_ROUTE_SUFFIX}",
                self.page_robots_import_legacy,
                ["POST"],
                "Import compatibility config into robot menu config",
            ),
            (
                f"{prefix}/{SYNC_ROUTE_SUFFIX}",
                self.page_sync_start,
                ["POST"],
                "Plugin dashboard menu sync",
            ),
            (
                f"{prefix}/{SYNC_EVENTS_ROUTE_SUFFIX}",
                self.page_sync_events,
                ["GET"],
                "Plugin dashboard menu sync progress (SSE)",
            ),
            (
                f"{prefix}/{LOG_EVENTS_ROUTE_SUFFIX}",
                self.page_log_events,
                ["GET"],
                "Plugin dashboard live logs (SSE)",
            ),
        )
        for route, handler, methods, description in routes:
            context.register_web_api(route, handler, methods, description)
        return True

    async def page_status(self) -> Any:
        web = _web()
        try:
            payload = self._status_payload()
        except MenuConfigError as exc:
            logger.error(f"{LOG_TAG} " + str(exc), exc_info=True)
            return web.error_response(str(exc), status_code=500)
        return web.json_response(payload)

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
            return web.error_response(
                t("common.error_separator").join(errors),
                status_code=400,
            )

        try:
            await self._save_config(values)
        except Exception as exc:
            logger.error(
                f"{LOG_TAG} " + t("web.config_save_failed", exc=exc),
                exc_info=True,
            )
            return web.error_response(
                t("web.config_save_failed", exc=exc),
                status_code=500,
            )

        syncer = self._get_syncer()
        if syncer is not None:
            syncer.set_config(self._get_config())
            syncer.set_platforms(self._platforms())
        return web.json_response(self._config_payload())

    async def page_robots_get(self) -> Any:
        web = _web()
        try:
            return web.json_response(self._robot_response())
        except MenuConfigError as exc:
            return web.error_response(str(exc), status_code=500)

    async def page_robots_save(self) -> Any:
        web = _web()
        if self._data_dir is None:
            return web.error_response(t("web.robot_config_unavailable"), status_code=503)
        payload = await web.request.json(default={})
        if not isinstance(payload, dict):
            return web.error_response(t("web.config_invalid_body"), status_code=400)

        async with self._config_lock:
            try:
                current = self._load_robot_config()
            except MenuConfigError as exc:
                return web.error_response(str(exc), status_code=500)
            submitted_version = payload.get("version")
            if type(submitted_version) is not int or submitted_version != current.get("version", 1):
                return web.error_response(
                    t("web.robot_version_conflict"),
                    status_code=409,
                )
            normalized, errors = validate_menu_config(current, payload)
            if errors:
                return web.error_response(
                    t("common.error_separator").join(errors),
                    status_code=400,
                )
            normalized["version"] = int(current.get("version", 1)) + 1
            try:
                save_menu_config(self._data_dir, normalized)
            except MenuConfigError as exc:
                return web.error_response(str(exc), status_code=500)
        return web.json_response(
            {
                **export_menu_config(normalized),
                "plugin": {"name": PLUGIN_NAME, "version": self._version},
            }
        )

    async def page_robots_import_legacy(self) -> Any:
        web = _web()
        if self._data_dir is None:
            return web.error_response(t("web.robot_config_unavailable"), status_code=503)
        payload = await web.request.json(default={})
        if not isinstance(payload, dict):
            return web.error_response(t("web.config_invalid_body"), status_code=400)
        appids = payload.get("appids")
        if not isinstance(appids, list) or not appids:
            return web.error_response(t("web.robot_import_appids_invalid"), status_code=400)

        async with self._config_lock:
            try:
                current = self._load_robot_config()
            except MenuConfigError as exc:
                return web.error_response(str(exc), status_code=500)
            submitted_version = payload.get("version")
            if type(submitted_version) is not int or submitted_version != current.get("version", 1):
                return web.error_response(
                    t("web.robot_version_conflict"),
                    status_code=409,
                )

            drafts = legacy_to_robot_drafts(
                self._get_config(),
                self._platforms(),
                [str(appid) for appid in appids],
            )
            robots = current.get("robots")
            merged = (
                [dict(item) for item in robots if isinstance(item, dict)]
                if isinstance(robots, list)
                else []
            )
            existing = {str(item.get("appid") or "") for item in merged}
            imported = 0
            for draft in drafts:
                if str(draft.get("appid") or "") in existing:
                    continue
                merged.append(draft)
                imported += 1
            if imported == 0:
                return web.error_response(t("web.robot_import_empty"), status_code=400)

            normalized, errors = validate_menu_config(
                current,
                {"robots": merged},
            )
            if errors:
                return web.error_response(
                    t("common.error_separator").join(errors),
                    status_code=400,
                )
            normalized["version"] = int(current.get("version", 1)) + 1
            try:
                save_menu_config(self._data_dir, normalized)
            except MenuConfigError as exc:
                return web.error_response(str(exc), status_code=500)
        return web.json_response(
            {
                **export_menu_config(normalized),
                "plugin": {"name": PLUGIN_NAME, "version": self._version},
                "imported": imported,
            }
        )

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

    async def page_log_events(self) -> Any:
        """SSE 推送插件日志；since 用于断线重连和页面重新打开后的回放。"""
        web = _web()
        log_buffer = self._log_buffer
        if log_buffer is None:
            return web.error_response(t("web.not_ready"), status_code=503)

        raw_since = web.request.query.get("since", "")
        try:
            since = max(0, int(raw_since))
        except (TypeError, ValueError):
            since = 0
        client_stream_id = web.request.query.get("streamId", "")
        stream_id = log_buffer.stream_id
        reset = (bool(client_stream_id) and client_stream_id != stream_id) or (
            since > log_buffer.last_seq
        )
        if reset:
            since = 0

        async def events():  # noqa: ANN202 - 流式响应体由宿主消费
            yield (
                "data: "
                + json.dumps(
                    {"type": "stream", "id": stream_id, "reset": reset},
                    ensure_ascii=False,
                )
                + "\n\n"
            )
            try:
                async for entry in log_buffer.follow(since):
                    if entry is None:
                        yield ": keep-alive\n\n"
                        continue
                    yield f"data: {json.dumps(entry.as_event(), ensure_ascii=False)}\n\n"
            except LogSubscriberLimitError:
                payload = {"type": "error", "code": "subscriber_limit"}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        return web.stream_response(events())

    def _make_run(
        self,
        syncer: MenuSynchronizer,
    ) -> Callable[[Callable[[dict[str, Any]], Awaitable[None]]], Awaitable[Any]]:
        async def run(emit: Callable[[dict[str, Any]], Awaitable[None]]) -> Any:
            syncer.set_config(self._get_config())
            syncer.set_platforms(self._platforms())

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
    log_buffer: LogBuffer | None = None,
    version: str = PLUGIN_VERSION,
) -> WebApiBundle | None:
    """注册 Dashboard Web API，宿主不支持时返回 None。"""
    bundle = WebApiBundle(
        get_syncer,
        get_config,
        get_platforms=get_platforms,
        save_config=save_config,
        data_dir=data_dir,
        log_buffer=log_buffer,
        version=version,
    )
    if not bundle.register(context):
        return None
    return bundle


__all__ = [
    "CONFIG_ROUTE_SUFFIX",
    "LOG_EVENTS_ROUTE_SUFFIX",
    "MENU_LIMITS",
    "ROBOTS_IMPORT_ROUTE_SUFFIX",
    "ROBOTS_ROUTE_SUFFIX",
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
