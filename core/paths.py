"""插件运行时数据目录解析。"""

from __future__ import annotations

import os
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path
from typing import Any

from astrbot.api import logger

from .i18n import LOG_TAG, t

PLUGIN_NAME = "astrbot_plugin_qq_custom_menu"
# 插件版本，与 metadata.yaml 的 version 保持一致；供 @register 与视图状态接口共用。
PLUGIN_VERSION = "v0.3.0"


def _call_or_none(func: Any, *args: Any) -> Path | None:
    try:
        value = func(*args) if callable(func) else func
        return Path(value) if value else None
    except Exception as exc:
        logger.debug("%s %s", LOG_TAG, t("log.data_dir_candidate_failed", exc=exc))
        return None


def _star_tools_data_dir(plugin_name: str) -> Path | None:
    for module_name in ("astrbot.api.star", "astrbot.core.star.star_tools"):
        try:
            module = import_module(module_name)
        except Exception as exc:
            logger.debug(
                "%s %s",
                LOG_TAG,
                t("log.optional_module_import_failed", module=module_name, exc=exc),
            )
            continue
        star_tools = getattr(module, "StarTools", None)
        get_data_dir = getattr(star_tools, "get_data_dir", None)
        path = _call_or_none(get_data_dir, plugin_name)
        if path is not None:
            return path
    return None


def _home_data_root() -> Path:
    """返回桌面版 AstrBot 的默认数据根目录。"""
    return Path.home() / ".astrbot"


def _iter_candidates(context: Any, plugin_name: str) -> Iterator[Path]:
    """按优先级产出候选目录，绝不回退到工作目录。"""
    star_tools_path = _star_tools_data_dir(plugin_name)
    if star_tools_path is not None:
        yield star_tools_path

    context_getter = getattr(context, "get_data_dir", None)
    context_path = _call_or_none(context_getter, plugin_name)
    if context_path is not None:
        yield context_path

    data_dir = getattr(context, "data_dir", None)
    context_attr_path = _call_or_none(data_dir)
    if context_attr_path is not None:
        yield context_attr_path / "plugin_data" / plugin_name

    env_root = os.environ.get("ASTRBOT_ROOT")
    if env_root:
        yield Path(env_root) / "data" / "plugin_data" / plugin_name

    try:
        home_root = _home_data_root()
    except Exception as exc:
        logger.debug("%s %s", LOG_TAG, t("log.home_data_root_failed", exc=exc))
        return
    yield home_root / "data" / "plugin_data" / plugin_name


def resolve_plugin_data_dir(context: Any, plugin_name: str = PLUGIN_NAME) -> Path:
    """解析并创建 AstrBot 插件数据目录。

    只使用 AstrBot 官方数据根或显式配置的数据根；工作目录不参与解析，
    避免在插件检出目录下写出运行时状态。
    """
    for candidate in _iter_candidates(context, plugin_name):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.debug("%s %s", LOG_TAG, t("log.data_dir_create_failed", exc=exc))
            continue
        return candidate

    raise RuntimeError(f"{LOG_TAG} {t('error.data_dir_unresolved')}")


__all__ = ["PLUGIN_NAME", "PLUGIN_VERSION", "resolve_plugin_data_dir"]
