"""插件配置读取与菜单结构校验。"""

from __future__ import annotations

from typing import Any


def _platform_entries(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result = []
    for entry in value:
        if not isinstance(entry, dict) or entry.get("enable") is False:
            continue
        appid = entry.get("appid") or entry.get("app_id")
        secret = (
            entry.get("secret")
            or entry.get("client_secret")
            or entry.get("clientSecret")
        )
        if appid and secret:
            result.append(
                {
                    "appid": str(appid),
                    "secret": str(secret),
                    "platform": str(entry.get("platform", "qq_official")),
                }
            )
    return result


def get_platforms(config: dict[str, Any], context: Any) -> list[dict[str, str]]:
    """优先读取插件配置中的凭证，否则兼容读取 AstrBot 平台配置。"""
    configured = _platform_entries(config.get("qq_platforms"))
    if configured:
        return configured
    for owner in (context, getattr(context, "config", None)):
        settings = getattr(owner, "platform_settings", None)
        if settings is None and isinstance(owner, dict):
            settings = owner.get("platform_settings")
        configured = _platform_entries(settings)
        if configured:
            return configured
    return []


def _menu_item(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    item_type = item.get("type")
    name = item.get("name")
    if item_type not in {"send_message", "link", "menu"} or not isinstance(name, str):
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
        result["sub_menu_items"] = [
            child for raw in children if (child := _menu_item(raw)) is not None
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
