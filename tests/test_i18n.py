"""core.i18n.Translator 的单元测试。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from core import i18n

TEST_ROOT = Path(__file__).resolve().parent / "_i18n_data"


@pytest.fixture(autouse=True)
def reset_i18n() -> None:
    """Each test restores the package locale singleton used by other tests."""
    yield
    i18n.initialize(Path(__file__).resolve().parents[1] / "core" / "i18n", i18n.DEFAULT_LANGUAGE)
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)


def write_locales(name: str) -> Path:
    locales = TEST_ROOT / name
    if locales.exists():
        shutil.rmtree(locales)
    locales.mkdir(parents=True)
    (locales / "zh-CN.json").write_text(
        json.dumps(
            {
                "hello": "你好，{name}",
                "fallback": "中文兜底",
                "bad_format": "值：{missing}",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (locales / "en-US.json").write_text(
        json.dumps(
            {
                "hello": "Hello, {name}",
                "fallback": "English fallback",
            }
        ),
        encoding="utf-8",
    )
    return locales


def test_default_language() -> None:
    translator = i18n.Translator(write_locales("default"))
    assert translator.language == i18n.DEFAULT_LANGUAGE
    assert translator.t("hello", name="世界") == "你好，世界"


def test_switch_language() -> None:
    translator = i18n.Translator(write_locales("switch"), "en-US")
    assert translator.language == "en-US"
    assert translator.t("hello", name="World") == "Hello, World"


def test_unknown_language_falls_back(caplog: Any) -> None:
    translator = i18n.Translator(write_locales("unknown"), "fr-FR")
    assert translator.language == i18n.DEFAULT_LANGUAGE
    assert "unsupported language" in caplog.text


def test_missing_file_falls_back(caplog: Any) -> None:
    locales = write_locales("missing-file")
    (locales / "en-US.json").unlink()
    translator = i18n.Translator(locales, "en-US")
    assert translator.language == i18n.DEFAULT_LANGUAGE
    assert translator.t("hello", name="世界") == "你好，世界"


def test_missing_key_returns_key() -> None:
    translator = i18n.Translator(write_locales("missing-key"))
    assert translator.t("missing.key") == "missing.key"


def test_fallback_to_zh_for_missing_key() -> None:
    translator = i18n.Translator(write_locales("fallback"), "en-US")
    assert translator.t("fallback") == "English fallback"
    assert translator.t("bad_format", other="x") == "值：{missing}"


def test_format_error_returns_template() -> None:
    translator = i18n.Translator(write_locales("format-error"))
    assert translator.t("bad_format", other="x") == "值：{missing}"


def test_module_initialize_and_get_instance() -> None:
    translator = i18n.initialize(write_locales("module"), "en-US")
    assert i18n.get_instance() is translator
    assert i18n.t("hello", name="Codex") == "Hello, Codex"
