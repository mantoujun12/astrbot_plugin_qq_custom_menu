"""日志与外部响应中的凭据脱敏工具。"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

MASK_VALUE = "******"

_SENSITIVE_KEY_PARTS = (
    "secret",
    "token",
    "password",
    "authorization",
    "credential",
    "apikey",
    "privatekey",
)
_SENSITIVE_TEXT = re.compile(
    r"(?i)(?P<prefix>(?:access[_-]?token|refresh[_-]?token|id[_-]?token|"
    r"client[_-]?secret|app[_-]?secret|api[_-]?key|authorization|password|secret)"
    r'["\']?\s*[:=]\s*["\']?)(?P<value>[^"\'\s,;}]+)'
)
_AUTH_SCHEME = re.compile(r"(?i)\b(QQBot|Bearer)\s+[A-Za-z0-9._~+/=-]+")


def _normalize_key(value: Any) -> str:
    return "".join(char for char in str(value).lower() if char.isalnum())


def _is_sensitive_key(value: Any) -> bool:
    normalized = _normalize_key(value)
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _known_values(values: Iterable[str]) -> tuple[str, ...]:
    unique = {str(value) for value in values if value is not None and len(str(value)) >= 4}
    return tuple(sorted(unique, key=len, reverse=True))


def redact_sensitive_text(value: str, *, known_values: Iterable[str] = ()) -> str:
    """脱敏文本中的凭据字段、认证头与已知敏感值。"""
    text = str(value)
    for secret in _known_values(known_values):
        text = text.replace(secret, MASK_VALUE)
    text = _AUTH_SCHEME.sub(lambda match: f"{match.group(1)} {MASK_VALUE}", text)
    return _SENSITIVE_TEXT.sub(
        lambda match: f"{match.group('prefix')}{MASK_VALUE}",
        text,
    )


def redact_sensitive_data(
    value: Any,
    *,
    known_values: Iterable[str] = (),
) -> Any:
    """递归脱敏外部响应中的敏感字段，同时保留结构方便排查。"""
    secrets = _known_values(known_values)
    if isinstance(value, Mapping):
        result: dict[Any, Any] = {}
        for key, item in value.items():
            result[key] = (
                MASK_VALUE
                if _is_sensitive_key(key)
                else redact_sensitive_data(item, known_values=secrets)
            )
        return result
    if isinstance(value, (list, tuple)):
        return [redact_sensitive_data(item, known_values=secrets) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value, known_values=secrets)
    return value


__all__ = ["MASK_VALUE", "redact_sensitive_data", "redact_sensitive_text"]
