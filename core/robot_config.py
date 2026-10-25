"""按机器人保存私聊自定义菜单配置。

新版配置独立存放在插件数据目录的 ``menu_config.json``，不会写进仓库。
每台机器人包含独立的凭证与 ``c2c`` 私聊菜单；兼容性配置仍在 AstrBot 的插件
配置中，运行时按 AppID 与新配置合并。
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .config import (
    MENU_LIMITS,
    QQ_PLATFORM_TYPES,
    SCENE_C2C,
    SCENES,
    _normalize_menu_entries,
    get_menu_entries,
    mask_appid,
    mask_secret,
)
from .i18n import t

MENU_CONFIG_FILENAME = "menu_config.json"


class MenuConfigError(ValueError):
    """新版机器人菜单配置读取、校验或保存失败。"""


def empty_menu_config() -> dict[str, Any]:
    return {"version": 1, "robots": []}


def _config_path(data_dir: str | Path) -> Path:
    return Path(data_dir) / MENU_CONFIG_FILENAME


def load_menu_config(data_dir: str | Path) -> dict[str, Any]:
    """读取新版机器人菜单配置。

    文件不存在时返回空结构；文件损坏或结构非法时抛错，避免静默回退兼容配置
    后意外覆盖线上内容。
    """
    path = _config_path(data_dir)
    if not path.exists():
        return empty_menu_config()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise MenuConfigError(t("robot.error.read_failed", path=path, exc=exc)) from exc
    except json.JSONDecodeError as exc:
        raise MenuConfigError(t("robot.error.invalid_json", exc=exc)) from exc

    if not isinstance(payload, dict):
        raise MenuConfigError(t("robot.error.top_level_object"))
    version = payload.get("version", 1)
    if type(version) is not int or version < 1:
        raise MenuConfigError(t("robot.error.version_invalid"))
    if not isinstance(payload.get("robots", []), list):
        raise MenuConfigError(t("robot.error.robots_type"))
    return payload


def save_menu_config(data_dir: str | Path, payload: dict[str, Any]) -> Path:
    """原子写入新版机器人菜单配置。"""
    target = _config_path(data_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd: int | None = None
    temp: Path | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
        )
        temp = Path(temp_name)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            fd = None
            file.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        os.replace(temp, target)
        temp = None
    except OSError as exc:
        raise MenuConfigError(t("robot.error.save_failed", path=target, exc=exc)) from exc
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if temp is not None:
            try:
                temp.unlink()
            except OSError:
                pass
    return target


def _existing_secrets(existing: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    robots = existing.get("robots")
    if not isinstance(robots, list):
        return result
    for robot in robots:
        if not isinstance(robot, dict):
            continue
        appid = str(robot.get("appid") or "").strip()
        secret = str(robot.get("secret") or "").strip()
        if appid and secret:
            result.setdefault(appid, secret)
    return result


def _normalize_scene(
    raw_scene: Any,
    *,
    robot_index: int,
) -> tuple[dict[str, Any], list[str]]:
    scene_path = f"robots[{robot_index}].scenes.{SCENE_C2C}"
    if not isinstance(raw_scene, dict):
        return {"enabled": False, "items": []}, [t("robot.error.scene_type", path=scene_path)]

    enabled = raw_scene.get("enabled", False)
    if not isinstance(enabled, bool):
        return {"enabled": False, "items": []}, [
            t("robot.error.scene_enabled_type", path=f"{scene_path}.enabled")
        ]

    entries, errors = _normalize_menu_entries(raw_scene.get("items", []))
    return {"enabled": enabled, "items": entries if not errors else []}, errors


def validate_menu_config(
    existing: dict[str, Any],
    payload: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """校验并归一化 Dashboard 提交的机器人私聊菜单配置。"""
    if not isinstance(payload, dict):
        return empty_menu_config(), [t("robot.error.payload_type")]
    raw_robots = payload.get("robots", [])
    if not isinstance(raw_robots, list):
        return empty_menu_config(), [t("robot.error.robots_list")]

    errors: list[str] = []
    robots: list[dict[str, Any]] = []
    seen_appids: set[str] = set()
    seen_ids: set[str] = set()
    secret_by_appid = _existing_secrets(existing)

    for index, raw_robot in enumerate(raw_robots):
        robot_path = f"robots[{index}]"
        if not isinstance(raw_robot, dict):
            errors.append(t("robot.error.robot_entry_type", path=robot_path))
            continue

        appid = str(raw_robot.get("appid") or "").strip()
        if not appid:
            errors.append(t("robot.error.appid_required", path=f"{robot_path}.appid"))
            continue
        if appid in seen_appids:
            errors.append(t("robot.error.appid_duplicate", path=f"{robot_path}.appid", appid=appid))
            continue
        seen_appids.add(appid)

        name = str(raw_robot.get("name") or "").strip()
        if not name:
            errors.append(t("robot.error.name_required", path=f"{robot_path}.name"))
            continue
        if len(name) > 64:
            errors.append(t("robot.error.name_too_long", path=f"{robot_path}.name", limit=64))
            continue

        platform = str(raw_robot.get("platform") or "").strip()
        if platform not in QQ_PLATFORM_TYPES:
            errors.append(
                t(
                    "robot.error.platform_unsupported",
                    path=f"{robot_path}.platform",
                    platform=platform,
                )
            )
            continue

        secret = str(raw_robot.get("secret") or "").strip()
        if not secret:
            secret = secret_by_appid.get(appid, "")
        if not secret:
            errors.append(t("robot.error.secret_required", path=f"{robot_path}.secret"))
            continue

        raw_scenes = raw_robot.get("scenes")
        if not isinstance(raw_scenes, dict):
            errors.append(t("robot.error.scenes_type", path=f"{robot_path}.scenes"))
            continue
        scene, scene_errors = _normalize_scene(
            raw_scenes.get(SCENE_C2C, {"enabled": False, "items": []}),
            robot_index=index,
        )
        if scene_errors:
            errors.extend(scene_errors)
            continue

        robot_id = str(raw_robot.get("id") or "").strip() or str(uuid.uuid4())
        if robot_id in seen_ids:
            errors.append(t("robot.error.id_duplicate", path=f"{robot_path}.id", id=robot_id))
            continue
        seen_ids.add(robot_id)

        robots.append(
            {
                "id": robot_id,
                "name": name,
                "appid": appid,
                "secret": secret,
                "platform": platform,
                "scenes": {SCENE_C2C: scene},
            }
        )

    if errors:
        return empty_menu_config(), errors
    return {"version": 1, "robots": robots}, []


def export_menu_config(config: dict[str, Any]) -> dict[str, Any]:
    """导出可安全返回 Dashboard 的配置，ClientSecret 只保留掩码。"""
    robots: list[dict[str, Any]] = []
    raw_robots = config.get("robots")
    if isinstance(raw_robots, list):
        for raw in raw_robots:
            if not isinstance(raw, dict):
                continue
            appid = str(raw.get("appid") or "").strip()
            if not appid:
                continue
            scenes = raw.get("scenes") if isinstance(raw.get("scenes"), dict) else {}
            c2c = scenes.get(SCENE_C2C) if isinstance(scenes, dict) else {}
            c2c = c2c if isinstance(c2c, dict) else {}
            secret = str(raw.get("secret") or "").strip()
            robots.append(
                {
                    "id": str(raw.get("id") or ""),
                    "name": str(raw.get("name") or ""),
                    "appid": appid,
                    "platform": str(raw.get("platform") or ""),
                    "secret_masked": mask_secret(secret),
                    "secret_set": bool(secret),
                    "scenes": {
                        SCENE_C2C: {
                            "enabled": bool(c2c.get("enabled", False)),
                            "items": get_menu_entries({"menu": c2c.get("items", [])}),
                        }
                    },
                }
            )

    version = config.get("version", 1)
    if type(version) is not int or version < 1:
        version = 1
    return {
        "version": version,
        "robots": robots,
        "available_scenes": list(SCENES),
        "menu_limits": dict(MENU_LIMITS),
    }


def _runtime_new_robots(config: dict[str, Any]) -> list[dict[str, Any]]:
    robots: list[dict[str, Any]] = []
    raw_robots = config.get("robots")
    if not isinstance(raw_robots, list):
        return robots
    for raw in raw_robots:
        if not isinstance(raw, dict):
            continue
        appid = str(raw.get("appid") or "").strip()
        secret = str(raw.get("secret") or "").strip()
        if not appid or not secret:
            continue
        raw_scenes = raw.get("scenes")
        raw_scene = raw_scenes.get(SCENE_C2C) if isinstance(raw_scenes, dict) else None
        raw_scene = raw_scene if isinstance(raw_scene, dict) else {}
        robots.append(
            {
                "id": str(raw.get("id") or appid),
                "name": str(raw.get("name") or appid),
                "appid": appid,
                "secret": secret,
                "platform": str(raw.get("platform") or "qq_official"),
                "source": "robot",
                "scenes": {
                    SCENE_C2C: {
                        "enabled": bool(raw_scene.get("enabled", False)),
                        "items": get_menu_entries({"menu": raw_scene.get("items", [])}),
                    }
                },
            }
        )
    return robots


def _runtime_legacy_robots(
    legacy_config: dict[str, Any],
    legacy_platforms: list[dict[str, str]],
) -> list[dict[str, Any]]:
    items = get_menu_entries(legacy_config)
    robots: list[dict[str, Any]] = []
    for platform in legacy_platforms:
        appid = str(platform.get("appid") or "").strip()
        secret = str(platform.get("secret") or "").strip()
        if not appid or not secret:
            continue
        robots.append(
            {
                "id": f"compatibility:{appid}",
                "name": str(platform.get("name") or mask_appid(appid)),
                "appid": appid,
                "secret": secret,
                "platform": str(platform.get("platform") or "qq_official"),
                "source": "compatibility",
                "scenes": {SCENE_C2C: {"enabled": True, "items": items}},
            }
        )
    return robots


def build_runtime_robots(
    legacy_config: dict[str, Any],
    robot_config: dict[str, Any],
    legacy_platforms: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """按 AppID 合并新版机器人与兼容配置，新版优先接管。"""
    robots = _runtime_new_robots(robot_config)
    managed_appids = {str(robot["appid"]) for robot in robots}
    robots.extend(
        robot
        for robot in _runtime_legacy_robots(legacy_config, legacy_platforms)
        if robot["appid"] not in managed_appids
    )
    return robots


def legacy_to_robot_drafts(
    legacy_config: dict[str, Any],
    legacy_platforms: list[dict[str, str]],
    appids: list[str],
) -> list[dict[str, Any]]:
    """把兼容配置中的指定 AppID 转换为新版机器人草稿。"""
    requested = {str(appid).strip() for appid in appids if str(appid).strip()}
    entries = get_menu_entries(legacy_config)
    drafts: list[dict[str, Any]] = []
    for platform in legacy_platforms:
        appid = str(platform.get("appid") or "").strip()
        if appid not in requested or not platform.get("secret"):
            continue
        drafts.append(
            {
                "name": str(platform.get("name") or mask_appid(appid)),
                "appid": appid,
                "secret": str(platform["secret"]),
                "platform": str(platform.get("platform") or "qq_official"),
                "scenes": {SCENE_C2C: {"enabled": True, "items": entries}},
            }
        )
    return drafts


def robot_item_counts(config: dict[str, Any]) -> dict[str, int]:
    """统计新版配置中的机器人数与私聊菜单条目数。"""
    robots = config.get("robots")
    result = {
        "robots": 0,
        "c2c_items": 0,
        "c2c_top_level": 0,
        "c2c_sub_items": 0,
    }
    if not isinstance(robots, list):
        return result
    for robot in robots:
        if not isinstance(robot, dict) or not str(robot.get("appid") or "").strip():
            continue
        result["robots"] += 1
        scenes = robot.get("scenes") if isinstance(robot.get("scenes"), dict) else {}
        c2c = scenes.get(SCENE_C2C) if isinstance(scenes, dict) else {}
        items = get_menu_entries({"menu": c2c.get("items", []) if isinstance(c2c, dict) else []})
        sub_items = sum(1 for item in items if item.get("parent"))
        result["c2c_items"] += len(items)
        result["c2c_sub_items"] += sub_items
        result["c2c_top_level"] += len(items) - sub_items
    return result


__all__ = [
    "MENU_CONFIG_FILENAME",
    "MenuConfigError",
    "build_runtime_robots",
    "empty_menu_config",
    "export_menu_config",
    "legacy_to_robot_drafts",
    "load_menu_config",
    "robot_item_counts",
    "save_menu_config",
    "validate_menu_config",
]
