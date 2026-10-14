"""插件运行时数据目录解析。"""

from __future__ import annotations

import os
from importlib import import_module
from pathlib import Path
from typing import Any

from astrbot.api import logger

LOG_TAG = "[qq-custom-menu]"
PLUGIN_NAME = "astrbot_plugin_qq_custom_menu"


def _call_or_none(func: Any, *args: Any) -> Path | None:
    try:
        value = func(*args) if callable(func) else func
        return Path(value) if value else None
    except Exception as exc:
        logger.debug("%s resolve plugin data dir candidate failed: %s", LOG_TAG, exc)
        return None


def _star_tools_data_dir(plugin_name: str) -> Path | None:
    for module_name in ("astrbot.api.star", "astrbot.core.star.star_tools"):
        try:
            module = import_module(module_name)
        except Exception as exc:
            logger.debug("%s import optional module %s failed: %s", LOG_TAG, module_name, exc)
            continue
        star_tools = getattr(module, "StarTools", None)
        get_data_dir = getattr(star_tools, "get_data_dir", None)
        path = _call_or_none(get_data_dir, plugin_name)
        if path is not None:
            return path
    return None


def resolve_plugin_data_dir(context: Any, plugin_name: str = PLUGIN_NAME) -> Path:
    """解析并创建 AstrBot 插件数据目录。"""
    candidates = []
    star_tools_path = _star_tools_data_dir(plugin_name)
    if star_tools_path is not None:
        candidates.append(star_tools_path)

    context_getter = getattr(context, "get_data_dir", None)
    context_path = _call_or_none(context_getter, plugin_name)
    if context_path is not None:
        candidates.append(context_path)

    data_dir = getattr(context, "data_dir", None)
    context_attr_path = _call_or_none(data_dir)
    if context_attr_path is not None:
        candidates.append(context_attr_path / "plugin_data" / plugin_name)

    env_root = os.environ.get("ASTRBOT_ROOT")
    if env_root:
        candidates.append(Path(env_root) / "data" / "plugin_data" / plugin_name)

    desktop_root = Path.home() / ".astrbot"
    candidates.append(desktop_root / "data" / "plugin_data" / plugin_name)
    candidates.append(Path.cwd() / "data" / "plugin_data" / plugin_name)

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.debug("%s create plugin data dir candidate failed: %s", LOG_TAG, exc)
            continue
        return candidate

    fallback = Path.cwd() / "data" / "plugin_data" / plugin_name
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


__all__ = ["PLUGIN_NAME", "resolve_plugin_data_dir"]