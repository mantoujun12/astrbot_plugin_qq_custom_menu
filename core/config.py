"""插件配置读取与菜单结构校验。"""

from __future__ import annotations

import re
from typing import Any

from astrbot.api import logger

from .i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, t

QQ_PLATFORM_TYPES = frozenset({"qq_official", "qq_official_webhook"})
SCENES = ("c2c",)
SCENE_C2C = "c2c"

# QQ 官方菜单限制：一级菜单最多 10 个，每个子菜单最多 5 个子项。
MENU_TOP_LEVEL_MAX = 10
MENU_SUB_ITEM_MAX = 5
MENU_LIMITS: dict[str, int] = {
    "top_level_max": MENU_TOP_LEVEL_MAX,
    "sub_items_max": MENU_SUB_ITEM_MAX,
}

# 插件视图主题默认色，与 web/dashboard/src/theme/index.ts 的浅色调色板保持一致。
DEFAULT_PRIMARY_COLOR = "#3c96ca"
DEFAULT_SECONDARY_COLOR = "#2f86bd"
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# template_list 模板 key -> QQ 菜单 type
_TEMPLATE_MENU_TYPES = {
    "switch": "switch",
    "send_message": "send_message",
    "link": "link",
    "menu": "menu",
}
_MENU_TYPES = frozenset({"switch", "send_message", "link", "menu"})
_SUB_MENU_TYPES = frozenset({"send_message", "link"})


def _platform_entries(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result = []
    for entry in value:
        if not isinstance(entry, dict) or entry.get("enable") is False:
            continue
        appid = entry.get("appid")
        secret = entry.get("secret")
        if appid and secret:
            result.append(
                {
                    "appid": str(appid),
                    "secret": str(secret),
                    # 插件配置用 platform 键，兼容旧配置的 type 键
                    "platform": str(entry.get("platform") or entry.get("type") or "qq_official"),
                }
            )
    return result


def get_plugin_platforms(config: dict[str, Any]) -> list[dict[str, str]]:
    """只读取插件配置里的平台凭证。"""
    return _platform_entries(config.get("qq_platforms"))


def get_platforms(config: dict[str, Any]) -> list[dict[str, str]]:
    """只读取插件配置中的兼容平台凭证。"""
    return get_plugin_platforms(config)


def _normalize_link(value: str) -> str | None:
    """把用户填写的链接规范为 QQ 要求的 https:// 开头格式。

    QQ 菜单接口要求链接必须以 https:// 开头（否则报 40030008 URL 格式错误），
    这里对省略协议或误用 http:// 的链接做容错补全。
    """
    value = value.strip()
    if not value:
        return None
    lowered = value.lower()
    if lowered.startswith("https://"):
        return "https://" + value[len("https://") :]
    if lowered.startswith("http://"):
        return "https://" + value[len("http://") :]
    if value.startswith("//"):
        return "https:" + value
    return "https://" + value


def _normalize_menu_item(
    item: Any, allowed_types: frozenset[str] = _MENU_TYPES
) -> dict[str, Any] | None:
    """把单个菜单项（新 template_list 或旧 dict 格式）归一化为内部结构。"""
    if not isinstance(item, dict):
        return None
    item_type = item.get("type") or _TEMPLATE_MENU_TYPES.get(item.get("__template_key"))
    name = item.get("name")
    if item_type not in allowed_types or not isinstance(name, str) or not name.strip():
        return None
    parent = item.get("parent")
    result: dict[str, Any] = {
        "type": item_type,
        "name": name.strip(),
        "parent": parent.strip() if isinstance(parent, str) else "",
    }
    if item_type == "send_message":
        message = item.get("send_message")
        if not isinstance(message, str):
            # 新模板把消息字段命名为 message
            message = item.get("message")
        if not isinstance(message, str):
            return None
        result["send_message"] = message
    elif item_type == "link":
        link = item.get("link")
        if not isinstance(link, str):
            return None
        normalized_link = _normalize_link(link)
        if normalized_link is None:
            return None
        result["link"] = normalized_link
    elif item_type == "switch":
        switch_id = item.get("switch_id")
        if not isinstance(switch_id, str) or not switch_id.strip():
            return None
        enabled = item.get("default", item.get("enabled", False))
        result["switch"] = {
            "switch_id": switch_id.strip(),
            "default": enabled if isinstance(enabled, bool) else False,
        }
    else:  # menu
        children = item.get("sub_menu_items", [])
        if not isinstance(children, list):
            children = []
        # 旧格式的子项内嵌在 sub_menu_items 中；新格式的子项是带 parent 的独立条目
        result["sub_menu_items"] = [
            child
            for raw in children
            if (child := _normalize_menu_item(raw, _SUB_MENU_TYPES)) is not None
        ]
    return result


def _to_qq_item(item: dict[str, Any]) -> dict[str, Any]:
    """去掉内部字段（如 parent），生成 QQ 接口要求的菜单项。"""
    result = {"type": item["type"], "name": item["name"]}
    if item["type"] == "send_message":
        result["send_message"] = item["send_message"]
    elif item["type"] == "link":
        result["link"] = item["link"]
    elif item["type"] == "switch":
        result["switch"] = dict(item["switch"])
    return result


def _raw_menu_entries(config: dict[str, Any]) -> list[Any]:
    raw = config.get("menu")
    if isinstance(raw, dict):  # 兼容旧版 {"items": [...]} 配置
        raw = raw.get("items", [])
    return raw if isinstance(raw, list) else []


def _build_menu(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """把归一化后的扁平私聊菜单条目组装成 QQ API 菜单树。"""
    # 新格式中，子菜单项通过 parent 字段引用所属一级菜单的名称
    pending_children: dict[str, list[dict[str, Any]]] = {}
    for item in entries:
        if item["type"] in _SUB_MENU_TYPES and item["parent"]:
            pending_children.setdefault(item["parent"], []).append(item)

    items: list[dict[str, Any]] = []
    for item in entries:
        if item["type"] == "menu":
            children = list(item["sub_menu_items"]) + pending_children.pop(item["name"], [])
            items.append(
                {
                    "type": "menu",
                    "name": item["name"],
                    "sub_menu_items": [_to_qq_item(child) for child in children],
                }
            )
        elif not item["parent"]:
            items.append(_to_qq_item(item))

    if pending_children:
        logger.warning(t("log.unmatched_parent", parents=", ".join(sorted(pending_children))))
    return {"items": items}


def menu_from_entries(entries: Any) -> dict[str, list[dict[str, Any]]]:
    """将 Dashboard/机器人配置中的扁平私聊菜单转换为 QQ 菜单树。"""
    if not isinstance(entries, list):
        return {"items": []}
    normalized = [
        item for raw in entries if (item := _normalize_menu_item(raw, _MENU_TYPES)) is not None
    ]
    return _build_menu(normalized)


def get_menu(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """将 WebUI 兼容配置转换为 QQ `/v2/menu` 请求体中的 menu 对象。"""
    return menu_from_entries(_raw_menu_entries(config))


def _migrate_entry(item: Any, parent: str) -> dict[str, Any] | None:
    if (
        not isinstance(item, dict)
        or not isinstance(item.get("name"), str)
        or not item["name"].strip()
    ):
        return None
    item_type = item.get("type")
    if item_type == "send_message" and isinstance(item.get("send_message"), str):
        return {
            "__template_key": "send_message",
            "name": item["name"],
            "message": item["send_message"],
            "parent": parent,
        }
    if item_type == "link" and isinstance(item.get("link"), str):
        return {
            "__template_key": "link",
            "name": item["name"],
            "link": item["link"],
            "parent": parent,
        }
    if item_type == "switch":
        switch = item.get("switch")
        if not isinstance(switch, dict):
            return None
        switch_id = switch.get("switch_id")
        if not isinstance(switch_id, str) or not switch_id.strip():
            return None
        return {
            "__template_key": "switch",
            "name": item["name"],
            "switch_id": switch_id,
            "default": bool(switch.get("default", False)),
            "parent": parent,
        }
    return None


def migrate_menu_config(config: Any) -> bool:
    """把旧版 dict 菜单配置迁移为 template_list 结构并保存。"""
    raw = config.get("menu")
    if not isinstance(raw, dict):
        return False

    legacy_items = raw.get("items", [])
    if not isinstance(legacy_items, list):
        legacy_items = []

    migrated: list[dict[str, Any]] = []
    for item in legacy_items:
        if not isinstance(item, dict):
            continue
        if (
            item.get("type") == "menu"
            and isinstance(item.get("name"), str)
            and item["name"].strip()
        ):
            migrated.append({"__template_key": "menu", "name": item["name"]})
            children = item.get("sub_menu_items", [])
            if isinstance(children, list):
                for child in children:
                    entry = _migrate_entry(child, parent=item["name"])
                    if entry is not None:
                        migrated.append(entry)
        else:
            entry = _migrate_entry(item, parent="")
            if entry is not None:
                migrated.append(entry)

    config["menu"] = migrated
    save = getattr(config, "save_config", None)
    if callable(save):
        save()
    logger.info(t("log.migration_done", count=len(migrated)))
    return True


# ---------------------------------------------------------------------------
# Dashboard 配置读写
# ---------------------------------------------------------------------------


def mask_appid(value: Any) -> str:
    """appid 脱敏：保留前 3 位与后 2 位，过短时整体打码。"""
    text = str(value or "")
    if len(text) <= 6:
        return "*" * len(text)
    return f"{text[:3]}{'*' * (len(text) - 5)}{text[-2:]}"


def mask_secret(value: Any) -> str:
    """ClientSecret 脱敏：只保留首尾各 2 位，绝不把明文回给前端。"""
    text = str(value or "")
    if len(text) <= 6:
        return "*" * len(text)
    return f"{text[:2]}{'*' * (len(text) - 4)}{text[-2:]}"


def get_theme_colors(config: dict[str, Any]) -> dict[str, str]:
    """读取插件视图主题色，缺失或非法值回退到默认配色。"""
    primary = config.get("primary_color")
    secondary = config.get("secondary_color")
    primary_text = primary.strip() if isinstance(primary, str) else ""
    secondary_text = secondary.strip() if isinstance(secondary, str) else ""
    return {
        "primary_color": (
            primary_text.lower() if _HEX_COLOR_RE.fullmatch(primary_text) else DEFAULT_PRIMARY_COLOR
        ),
        "secondary_color": (
            secondary_text.lower()
            if _HEX_COLOR_RE.fullmatch(secondary_text)
            else DEFAULT_SECONDARY_COLOR
        ),
    }


def _editor_entry_append(
    entries: list[dict[str, Any]],
    item: dict[str, Any],
    parent: str,
) -> None:
    """把归一化后的菜单项追加成 Dashboard 使用的扁平结构，并递归展开旧式子项。"""
    entry: dict[str, Any] = {"type": item["type"], "name": item["name"], "parent": parent}
    if item["type"] == "send_message":
        entry["message"] = item["send_message"]
    elif item["type"] == "link":
        entry["link"] = item["link"]
    elif item["type"] == "switch":
        entry["switch_id"] = item["switch"]["switch_id"]
        entry["default"] = item["switch"]["default"]
    entries.append(entry)
    for child in item.get("sub_menu_items", []):
        _editor_entry_append(entries, child, parent=item["name"])


def get_menu_entries(config: dict[str, Any]) -> list[dict[str, Any]]:
    """把配置里的菜单转换为 Dashboard 编辑用的扁平条目列表。

    新格式中一级菜单与子项本来就是扁平存储；旧格式的子项内嵌在
    ``sub_menu_items`` 里，这里一并展开，输出顺序保持「母菜单 → 子项」。
    """
    entries: list[dict[str, Any]] = []
    for raw in _raw_menu_entries(config):
        item = _normalize_menu_item(raw, _MENU_TYPES)
        if item is None:
            continue
        parent = item["parent"] if item["type"] in _SUB_MENU_TYPES else ""
        _editor_entry_append(entries, item, parent=parent)
    return entries


def menu_stats(config: dict[str, Any]) -> dict[str, int]:
    """统计一级菜单与子项数量，供状态页与保存前校验共用。"""
    entries = get_menu_entries(config)
    sub_items = sum(1 for entry in entries if entry["parent"])
    return {
        "top_level": len(entries) - sub_items,
        "sub_items": sub_items,
        "total": len(entries),
        **MENU_LIMITS,
    }


def _export_plugin_platforms(config: dict[str, Any]) -> list[dict[str, Any]]:
    """导出插件配置里的平台条目，secret 只回掩码。"""
    raw_platforms = config.get("qq_platforms")
    if not isinstance(raw_platforms, list):
        return []
    platforms: list[dict[str, Any]] = []
    for raw in raw_platforms:
        if not isinstance(raw, dict):
            continue
        secret = str(raw.get("secret") or "")
        platforms.append(
            {
                "appid": str(raw.get("appid") or ""),
                "platform": str(raw.get("platform") or raw.get("type") or "qq_official"),
                "secret_masked": mask_secret(secret),
                "secret_set": bool(secret),
            }
        )
    return platforms


def _runtime_platforms(
    config: dict[str, Any],
    overrides: list[dict[str, str]] | None,
) -> list[dict[str, Any]]:
    """导出兼容配置中当前生效的平台列表。"""
    raw = overrides if overrides is not None else get_plugin_platforms(config)
    result: list[dict[str, Any]] = []
    for entry in raw:
        secret = str(entry.get("secret") or "")
        result.append(
            {
                "pf_id": mask_appid(entry.get("appid")),
                "appid": mask_appid(entry.get("appid")),
                "platform": str(entry.get("platform") or "qq_official"),
                "secret_set": bool(secret),
                "source": "plugin",
            }
        )
    return result


def export_config(
    config: dict[str, Any],
    runtime_platforms: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """导出 Dashboard 配置接口的响应体。"""
    plugin_platforms = _export_plugin_platforms(config)
    return {
        "language": str(config.get("language") or DEFAULT_LANGUAGE),
        "sync_menu": config.get("sync_menu", True) is not False,
        **get_theme_colors(config),
        "qq_platforms": plugin_platforms,
        "runtime_platforms": _runtime_platforms(config, runtime_platforms),
        "menu": get_menu_entries(config),
        "limits": dict(MENU_LIMITS),
    }


def _normalize_platforms(
    existing: dict[str, Any],
    raw_platforms: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    """校验并归一化 Dashboard 提交的平台条目。

    secret 留空表示沿用同 appid 的已保存密钥；新增平台必须提供密钥。
    """
    if not isinstance(raw_platforms, list):
        return [], [t("web.config_platforms_invalid")]

    existing_secrets: dict[str, str] = {}
    raw_existing = existing.get("qq_platforms")
    if isinstance(raw_existing, list):
        for entry in raw_existing:
            if isinstance(entry, dict):
                appid = str(entry.get("appid") or "").strip()
                secret = str(entry.get("secret") or "")
                if appid and secret:
                    existing_secrets[appid] = secret

    platforms: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw_platforms, start=1):
        if not isinstance(entry, dict):
            errors.append(t("web.config_platform_invalid", index=index))
            continue
        appid = str(entry.get("appid") or "").strip()
        if not appid:
            errors.append(t("web.config_appid_empty", index=index))
            continue
        if appid in seen:
            errors.append(t("web.config_appid_duplicate", appid=appid))
            continue
        seen.add(appid)

        platform = str(entry.get("platform") or "qq_official").strip()
        if platform not in QQ_PLATFORM_TYPES:
            errors.append(t("web.config_platform_type_invalid", appid=appid))
            continue

        secret = str(entry.get("secret") or "").strip()
        if not secret:
            secret = existing_secrets.get(appid, "")
        if not secret:
            errors.append(t("web.config_secret_required", appid=appid))
            continue

        platforms.append(
            {
                "__template_key": "qq_platform",
                "appid": appid,
                "secret": secret,
                "platform": platform,
            }
        )
    return platforms, errors


def _normalize_menu_entries(raw_menu: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """校验 Dashboard 提交的菜单条目，返回 template_list 结构。"""
    if not isinstance(raw_menu, list):
        return [], [t("web.config_menu_invalid")]

    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    top_level_names: list[str] = []
    menu_names: set[str] = set()
    child_counts: dict[str, int] = {}
    switch_ids: set[str] = set()

    for index, raw in enumerate(raw_menu, start=1):
        if not isinstance(raw, dict):
            errors.append(t("web.config_menu_entry_invalid", index=index))
            continue
        item_type = str(raw.get("type") or "")
        name = str(raw.get("name") or "").strip()
        parent = str(raw.get("parent") or "").strip()

        if item_type not in _MENU_TYPES:
            errors.append(t("web.config_menu_type_invalid", index=index))
            continue
        if not name:
            errors.append(t("web.config_menu_name_empty", index=index))
            continue

        if item_type == "menu":
            if parent:
                errors.append(t("web.config_menu_parent_not_allowed", name=name))
                continue
            menu_names.add(name)
            top_level_names.append(name)
            entries.append({"__template_key": "menu", "name": name})
            continue

        if item_type == "switch":
            if parent:
                errors.append(t("web.config_switch_parent_not_allowed", name=name))
                continue
            switch_id = str(raw.get("switch_id") or "").strip()
            if not switch_id:
                errors.append(t("web.config_menu_switch_id_empty", name=name))
                continue
            if switch_id in switch_ids:
                errors.append(t("web.config_menu_switch_id_duplicate", switch_id=switch_id))
                continue
            switch_ids.add(switch_id)
            top_level_names.append(name)
            entries.append(
                {
                    "__template_key": "switch",
                    "name": name,
                    "switch_id": switch_id,
                    "default": bool(raw.get("default", False)),
                }
            )
            continue

        if not parent:
            top_level_names.append(name)
        else:
            child_counts[parent] = child_counts.get(parent, 0) + 1

        if item_type == "send_message":
            message = raw.get("message")
            if not isinstance(message, str) or not message.strip():
                errors.append(t("web.config_menu_message_empty", name=name))
                continue
            entries.append(
                {
                    "__template_key": "send_message",
                    "name": name,
                    "message": message.strip(),
                    "parent": parent,
                }
            )
            continue

        link = raw.get("link")
        normalized_link = _normalize_link(link) if isinstance(link, str) else None
        if normalized_link is None:
            errors.append(t("web.config_menu_link_empty", name=name))
            continue
        entries.append(
            {
                "__template_key": "link",
                "name": name,
                "link": normalized_link,
                "parent": parent,
            }
        )

    if len(top_level_names) > MENU_TOP_LEVEL_MAX:
        errors.append(t("web.config_menu_top_limit", max=MENU_TOP_LEVEL_MAX))
    if len(set(top_level_names)) != len(top_level_names):
        errors.append(t("web.config_menu_duplicate"))
    for entry in entries:
        parent = str(entry.get("parent") or "")
        if parent and parent not in menu_names:
            errors.append(t("web.config_menu_parent_invalid", name=entry["name"], parent=parent))
    for name, count in child_counts.items():
        if count > MENU_SUB_ITEM_MAX:
            errors.append(t("web.config_menu_sub_limit", name=name, max=MENU_SUB_ITEM_MAX))

    return entries, errors


def normalize_config_payload(
    existing: dict[str, Any],
    payload: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """校验 Dashboard 提交的配置，返回（可写回的字段，错误列表）。

    载荷允许只带部分字段，缺省字段沿用已保存的值，避免「设置」页与「菜单」页
    互相覆盖。任一字段出错时整次保存都会被拒绝。
    """
    values: dict[str, Any] = {}
    errors: list[str] = []

    if "language" in payload:
        language = payload.get("language")
        if not isinstance(language, str) or language not in SUPPORTED_LANGUAGES:
            errors.append(
                t("web.config_language_invalid", languages=" / ".join(SUPPORTED_LANGUAGES))
            )
        else:
            values["language"] = language

    if "sync_menu" in payload:
        sync_menu = payload.get("sync_menu")
        if not isinstance(sync_menu, bool):
            errors.append(t("web.config_sync_menu_invalid"))
        else:
            values["sync_menu"] = sync_menu

    for field in ("primary_color", "secondary_color"):
        if field not in payload:
            continue
        raw_color = payload.get(field)
        color = raw_color.strip() if isinstance(raw_color, str) else ""
        if not _HEX_COLOR_RE.fullmatch(color):
            errors.append(t("web.config_theme_color_invalid", field=field))
        else:
            values[field] = color.lower()

    if "qq_platforms" in payload:
        platforms, platform_errors = _normalize_platforms(existing, payload.get("qq_platforms"))
        errors.extend(platform_errors)
        if not platform_errors:
            values["qq_platforms"] = platforms

    if "menu" in payload:
        menu, menu_errors = _normalize_menu_entries(payload.get("menu"))
        errors.extend(menu_errors)
        if not menu_errors:
            values["menu"] = menu

    return values, errors


__all__ = [
    "DEFAULT_PRIMARY_COLOR",
    "DEFAULT_SECONDARY_COLOR",
    "MENU_LIMITS",
    "MENU_SUB_ITEM_MAX",
    "MENU_TOP_LEVEL_MAX",
    "QQ_PLATFORM_TYPES",
    "SCENE_C2C",
    "SCENES",
    "export_config",
    "get_menu",
    "get_menu_entries",
    "get_platforms",
    "get_plugin_platforms",
    "get_theme_colors",
    "mask_appid",
    "mask_secret",
    "menu_from_entries",
    "menu_stats",
    "migrate_menu_config",
    "normalize_config_payload",
]
