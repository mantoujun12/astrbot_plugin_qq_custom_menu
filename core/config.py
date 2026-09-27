"""插件配置读取与菜单结构校验。"""

from __future__ import annotations

from typing import Any

QQ_PLATFORM_TYPES = frozenset({"qq_official", "qq_official_webhook"})
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


def _menu_item(item: Any, allowed_types: frozenset[str] = _MENU_TYPES) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    item_type = item.get("type")
    name = item.get("name")
    if item_type not in allowed_types or not isinstance(name, str):
        return None
    result: dict[str, Any] = {"type": item_type, "name": name}
    if item_type == "send_message" and isinstance(item.get("send_message"), str):
        result["send_message"] = item["send_message"]
    elif item_type == "link" and isinstance(item.get("link"), str):
        result["link"] = item["link"]
    elif item_type == "menu":
        children = item.get("sub_menu_items", [])
        if not isinstance(children, list):
            return None
        # 官方接口二级菜单只允许 send_message / link，出现 menu 会整单被拒（40030014）
        result["sub_menu_items"] = [
            child for raw in children if (child := _menu_item(raw, _SUB_MENU_TYPES)) is not None
        ]
    else:
        return None
    return result


def get_menu(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """将 WebUI 配置转换为 QQ `/v2/menu` 请求体中的 menu 对象。"""
    raw = config.get("menu", {}).get("items", []) if isinstance(config.get("menu"), dict) else []
    if not isinstance(raw, list):
        raw = []
    return {"items": [item for raw_item in raw if (item := _menu_item(raw_item)) is not None]}
