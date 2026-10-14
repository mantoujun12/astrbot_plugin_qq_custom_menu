"""菜单同步状态持久化与变更检测。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from astrbot.api import logger

LOG_TAG = "[qq-custom-menu]"
STATE_FILENAME = "menu_state.yaml"


class MenuStateStore:
    """记录每个 appid 上次成功同步的菜单摘要。"""

    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / STATE_FILENAME

    def load(self) -> dict[str, str]:
        if not self.state_file.exists():
            return {}
        try:
            with self.state_file.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
        except Exception as exc:
            logger.warning("%s load menu state failed: %s", LOG_TAG, exc)
            return {}
        if not isinstance(data, dict):
            logger.warning("%s menu state is not a mapping, ignored", LOG_TAG)
            return {}
        return {str(key): str(value) for key, value in data.items() if value}

    def save(self, state: dict[str, str]) -> None:
        tmp_file = self.state_file.with_suffix(".yaml.tmp")
        try:
            with tmp_file.open("w", encoding="utf-8") as file:
                yaml.safe_dump(state, file, allow_unicode=True, sort_keys=False)
            tmp_file.replace(self.state_file)
        except Exception as exc:
            logger.warning("%s save menu state failed: %s", LOG_TAG, exc)
            try:
                if tmp_file.exists():
                    tmp_file.unlink()
            except Exception as cleanup_exc:
                logger.debug("%s cleanup menu state tmp failed: %s", LOG_TAG, cleanup_exc)

    def is_unchanged(self, appid: str, menu: dict[str, Any]) -> bool:
        return self.load().get(appid) == menu_digest(menu)

    def mark_synced(self, appid: str, menu: dict[str, Any]) -> None:
        state = self.load()
        state[appid] = menu_digest(menu)
        self.save(state)


def menu_digest(menu: dict[str, Any]) -> str:
    """生成稳定摘要，用于判断菜单内容是否变化。"""
    payload = json.dumps(menu, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = ["STATE_FILENAME", "MenuStateStore", "menu_digest"]