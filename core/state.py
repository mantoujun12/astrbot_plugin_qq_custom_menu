"""菜单同步状态持久化与变更检测。"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml
from astrbot.api import logger

LOG_TAG = "[qq-custom-menu]"
STATE_FILENAME = "menu_state.yaml"
LOCK_TIMEOUT_SECONDS = 2.0
LOCK_STALE_SECONDS = 30.0


class MenuStateStore:
    """记录每个 appid 上次成功同步的菜单摘要。"""

    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / STATE_FILENAME
        self.lock_file = self.state_file.with_suffix(".yaml.lock")

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
        with self._locked():
            self._write(state)

    def is_unchanged(self, appid: str, menu: dict[str, Any]) -> bool:
        return self.load().get(appid) == menu_digest(menu)

    def mark_synced(self, appid: str, menu: dict[str, Any]) -> None:
        with self._locked():
            state = self.load()
            state[appid] = menu_digest(menu)
            self._write(state)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        """用独占锁文件跨进程串行化状态更新。"""
        acquired = False
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            try:
                fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd)
                acquired = True
                break
            except FileExistsError:
                try:
                    age = time.time() - self.lock_file.stat().st_mtime
                except OSError:
                    age = 0.0
                if age > LOCK_STALE_SECONDS:
                    try:
                        self.lock_file.unlink()
                    except OSError as exc:
                        logger.debug("%s remove stale state lock failed: %s", LOG_TAG, exc)
                    continue
                time.sleep(0.05)
            except OSError as exc:
                logger.warning("%s acquire state lock failed: %s", LOG_TAG, exc)
                break

        if not acquired:
            logger.warning(
                "%s state lock unavailable, write without lock: %s", LOG_TAG, self.lock_file
            )
        try:
            yield
        finally:
            if acquired:
                try:
                    self.lock_file.unlink()
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    logger.debug("%s release state lock failed: %s", LOG_TAG, exc)

    def _write(self, state: dict[str, str]) -> None:
        """原子写入状态，临时文件必须唯一以避免并发覆盖。"""
        fd: int | None = None
        tmp_path: Path | None = None
        try:
            fd, tmp_name = tempfile.mkstemp(
                prefix=f"{self.state_file.name}.",
                suffix=".tmp",
                dir=self.data_dir,
            )
            tmp_path = Path(tmp_name)
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                fd = None
                yaml.safe_dump(state, file, allow_unicode=True, sort_keys=False)
            os.replace(tmp_path, self.state_file)
            tmp_path = None
        except Exception as exc:
            logger.warning("%s save menu state failed: %s", LOG_TAG, exc)
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError as exc:
                    logger.debug("%s close state tmp failed: %s", LOG_TAG, exc)
            if tmp_path is not None:
                try:
                    tmp_path.unlink()
                except OSError as cleanup_exc:
                    logger.debug("%s cleanup menu state tmp failed: %s", LOG_TAG, cleanup_exc)


def menu_digest(menu: dict[str, Any]) -> str:
    """生成稳定摘要，用于判断菜单内容是否变化。"""
    payload = json.dumps(menu, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = ["STATE_FILENAME", "MenuStateStore", "menu_digest"]
