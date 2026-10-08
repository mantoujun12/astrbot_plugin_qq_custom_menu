"""插件配置读取与菜单结构校验。"""

from __future__ import annotations

from typing import Any

from astrbot.api import logger

QQ_PLATFORM_TYPES = frozenset({"qq_official", "qq_official_webhook"})

# template_list 模板 key -> QQ 菜单 type
_TEMPLATE_MENU_TYPES = {
    "send_message": "send_message",
    "link": "link",
    "menu": "menu",
}
_MENU_TYPES = frozenset({"send_message", "link", "menu"})
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
                    # 插件配置用 platform 键，AstrBot 平台配置用 type 键
                    "platform": str(entry.get("platform") or entry.get("type") or "qq_official"),
                }
            )
    return result


def get_platforms(config: dict[str, Any], context: Any) -> list[dict[str, str]]:
    """优先读取插件配置中的凭证，留空时回退读取 AstrBot 全局配置中的 QQ 官方平台。"""
    configured = _platform_entries(config.get("qq_platforms"))
    if configured:
        return configured
    astrbot = _platform_entries(context.get_config().get("platform", []))
    return [entry for entry in astrbot if entry["platform"] in QQ_PLATFORM_TYPES]


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
        if not isinstance(item.get("link"), str):
            return None
        result["link"] = item["link"]
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
    return result


def _raw_menu_entries(config: dict[str, Any]) -> list[Any]:
    raw = config.get("menu")
    if isinstance(raw, dict):  # 兼容旧版 {"items": [...]} 配置
        raw = raw.get("items", [])
    return raw if isinstance(raw, list) else []


def get_menu(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """将 WebUI 配置转换为 QQ `/v2/menu` 请求体中的 menu 对象。"""
    entries = [
        item
        for raw in _raw_menu_entries(config)
        if (item := _normalize_menu_item(raw, _MENU_TYPES)) is not None
    ]

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
        logger.warning(
            "菜单配置中存在未匹配到子菜单的条目，已忽略: parent=%s",
            ", ".join(sorted(pending_children)),
        )
    return {"items": items}


def _migrate_entry(item: Any, parent: str) -> dict[str, Any] | None:
    if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
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
        if item.get("type") == "menu" and isinstance(item.get("name"), str) and item["name"].strip():
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
    logger.info("已将旧版菜单配置迁移为 template_list 格式，共 %d 个菜单项", len(migrated))
    return True
