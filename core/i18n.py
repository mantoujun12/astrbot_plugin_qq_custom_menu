"""轻量级国际化（i18n）支持。

加载 `core/i18n/<lang>.json` 扁平翻译表，提供模块级单例与便捷函数 `t`。
运行时日志与 WebUI 文案分属两条 i18n 管线：
- `core/i18n/*.json`：运行时 flat key，由本模块读取。
- `.astrbot-plugin/i18n/*.json`：WebUI metadata/config，由 AstrBot 宿主读取。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from astrbot.api import logger

SUPPORTED_LANGUAGES: tuple[str, ...] = ("zh-CN", "en-US", "ru-RU", "ja-JP")
DEFAULT_LANGUAGE: str = "zh-CN"
LOG_TAG: str = "[qq-custom-menu]"

_instance: Translator | None = None


class Translator:
    """JSON 翻译加载器与带默认语言回退的 key 查找器。"""

    def __init__(
        self,
        locales_dir: Path | str,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        self.locales_dir = Path(locales_dir)
        self._fallback_lang = DEFAULT_LANGUAGE
        self._active: dict[str, str] = {}
        self._fallback: dict[str, str] = {}
        self._language = DEFAULT_LANGUAGE
        # fallback 字典先加载好，保证后续 set_language 失败时仍可用
        self._fallback = self._load_dict(self._fallback_lang)
        self.set_language(language)

    @property
    def language(self) -> str:
        """当前生效的语言。"""
        return self._language

    def set_language(self, language: str | None) -> None:
        """切换语言，未识别或文件缺失时回退到默认语言。"""
        if not isinstance(language, str):
            language = DEFAULT_LANGUAGE
        target = (language or DEFAULT_LANGUAGE).strip()
        if target not in SUPPORTED_LANGUAGES:
            logger.warning(
                "%s %s",
                LOG_TAG,
                self._diagnostic(
                    "log.unsupported_language",
                    f"unsupported language={target!r}, fallback to {DEFAULT_LANGUAGE}",
                    language=target,
                    fallback=DEFAULT_LANGUAGE,
                ),
            )
            target = DEFAULT_LANGUAGE
        if target == self._fallback_lang:
            self._active = self._fallback
        else:
            loaded = self._load_dict(target)
            if not loaded:
                logger.warning(
                    "%s %s",
                    LOG_TAG,
                    self._diagnostic(
                        "log.locale_not_loaded",
                        f"no translations loaded for {target}, fallback to {DEFAULT_LANGUAGE}",
                        language=target,
                        fallback=DEFAULT_LANGUAGE,
                    ),
                )
                self._active = self._fallback
                target = DEFAULT_LANGUAGE
            else:
                self._active = loaded
        self._language = target

    def t(self, key: str, **kwargs: Any) -> str:
        """按 key 查找翻译，缺失返回 key，格式化失败返回原始模板。"""
        template = self._active.get(key)
        if template is None:
            template = self._fallback.get(key)
        if template is None:
            return key
        if not kwargs:
            return template
        try:
            return template.format(**kwargs)
        except Exception as exc:
            logger.debug(
                "%s %s",
                LOG_TAG,
                self._diagnostic(
                    "log.i18n_format_failed",
                    f"i18n format failed key={key} kwargs={kwargs}: {exc}",
                    key=key,
                    kwargs=kwargs,
                    exc=exc,
                ),
            )
            return template

    def _diagnostic(self, message_key: str, default: str, /, **kwargs: Any) -> str:
        """翻译 i18n 自身诊断；兜底词典未加载时使用英文 fallback。"""
        template = self._active.get(message_key) or self._fallback.get(message_key) or default
        try:
            return template.format(**kwargs)
        except Exception:
            return default

    def _load_dict(self, language: str) -> dict[str, str]:
        """加载一个语言的 JSON 文件，任何失败都降级为空字典。"""
        path = self.locales_dir / f"{language}.json"
        if not path.exists():
            logger.warning(
                "%s %s",
                LOG_TAG,
                self._diagnostic(
                    "log.locale_file_missing",
                    f"locale file not found: {path}",
                    path=path,
                ),
            )
            return {}
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception as exc:
            logger.warning(
                "%s %s",
                LOG_TAG,
                self._diagnostic(
                    "log.locale_load_failed",
                    f"failed to load locale {path}: {exc}",
                    path=path,
                    exc=exc,
                ),
            )
            return {}
        if not isinstance(data, dict):
            logger.warning(
                "%s %s",
                LOG_TAG,
                self._diagnostic(
                    "log.locale_not_object",
                    f"locale {path} is not a JSON object, ignored",
                    path=path,
                ),
            )
            return {}
        return {str(key): value for key, value in data.items() if isinstance(value, str)}


def initialize(locales_dir: Path | str, language: str = DEFAULT_LANGUAGE) -> Translator:
    """初始化（或重置）模块级单例。"""
    global _instance
    _instance = Translator(locales_dir, language)
    return _instance


def get_instance() -> Translator:
    """获取单例，未初始化时惰性创建默认 zh-CN 实例。"""
    global _instance
    if _instance is None:
        _instance = Translator(Path(__file__).resolve().parent / "i18n", DEFAULT_LANGUAGE)
    return _instance


def t(key: str, **kwargs: Any) -> str:
    """便捷翻译函数。"""
    return get_instance().t(key, **kwargs)


__all__ = [
    "DEFAULT_LANGUAGE",
    "LOG_TAG",
    "SUPPORTED_LANGUAGES",
    "Translator",
    "get_instance",
    "initialize",
    "t",
]
