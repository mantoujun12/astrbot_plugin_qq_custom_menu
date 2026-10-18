"""core.i18n.Translator 的单元测试。"""

from __future__ import annotations

import json
import logging
import shutil
import string
from pathlib import Path
from typing import Any

import pytest

from core import i18n

TEST_ROOT = Path(__file__).resolve().parent / "_i18n_data"
REAL_LOCALES = Path(__file__).resolve().parents[1] / "core" / "i18n"


@pytest.fixture(autouse=True)
def reset_i18n() -> None:
    """Each test restores the package locale singleton used by other tests."""
    yield
    i18n.initialize(REAL_LOCALES, i18n.DEFAULT_LANGUAGE)
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


def load_locale(language: str) -> dict[str, str]:
    data = json.loads((REAL_LOCALES / f"{language}.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def placeholders(template: str) -> set[str]:
    return {
        field_name
        for _literal, field_name, _format_spec, _conversion in string.Formatter().parse(template)
        if field_name
    }


def test_default_language() -> None:
    translator = i18n.Translator(write_locales("default"))
    assert translator.language == i18n.DEFAULT_LANGUAGE
    assert translator.t("hello", name="世界") == "你好，世界"


def test_switch_language() -> None:
    translator = i18n.Translator(write_locales("switch"), "en-US")
    assert translator.language == "en-US"
    assert translator.t("hello", name="World") == "Hello, World"


def test_switch_to_new_locales() -> None:
    translator = i18n.Translator(REAL_LOCALES, "ru-RU")
    assert translator.language == "ru-RU"
    assert translator.t("log.no_platforms") == (
        "учётные данные официального бота QQ не настроены, "
        "синхронизация пользовательского меню пропущена"
    )

    translator.set_language("ja-JP")
    assert translator.language == "ja-JP"
    assert translator.t("log.no_platforms") == (
        "QQ 公式ボットの認証情報が未設定のため、カスタムメニューの同期をスキップしました"
    )


def test_unknown_language_falls_back(caplog: Any) -> None:
    translator = i18n.Translator(write_locales("unknown"), "fr-FR")
    assert translator.language == i18n.DEFAULT_LANGUAGE
    assert "unsupported language" in caplog.text


def test_diagnostic_uses_active_language(caplog: Any) -> None:
    translator = i18n.Translator(REAL_LOCALES, "ja-JP")

    with caplog.at_level(logging.WARNING, logger="astrbot"):
        translator.set_language("fr-FR")

    assert translator.language == i18n.DEFAULT_LANGUAGE
    assert "サポートされていない" in caplog.text


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


def test_non_string_language_falls_back() -> None:
    translator = i18n.Translator(write_locales("non-string-language"), None)  # type: ignore[arg-type]
    assert translator.language == i18n.DEFAULT_LANGUAGE
    assert translator.t("hello", name="世界") == "你好，世界"


def test_invalid_json_falls_back(caplog: Any) -> None:
    locales = write_locales("invalid-json")
    (locales / "en-US.json").write_text("{not json", encoding="utf-8")

    translator = i18n.Translator(locales, "en-US")

    assert translator.language == i18n.DEFAULT_LANGUAGE
    assert "load locale" in caplog.text


def test_non_object_json_falls_back(caplog: Any) -> None:
    locales = write_locales("non-object-json")
    (locales / "en-US.json").write_text("[]", encoding="utf-8")

    translator = i18n.Translator(locales, "en-US")

    assert translator.language == i18n.DEFAULT_LANGUAGE
    assert "not a JSON object" in caplog.text


def test_supported_languages_have_locale_files() -> None:
    assert i18n.SUPPORTED_LANGUAGES == ("zh-CN", "en-US", "ru-RU", "ja-JP")
    for language in i18n.SUPPORTED_LANGUAGES:
        assert (REAL_LOCALES / f"{language}.json").is_file(), language


def test_locale_files_keep_the_same_key_set() -> None:
    expected = set(load_locale(i18n.DEFAULT_LANGUAGE))
    for language in i18n.SUPPORTED_LANGUAGES:
        assert set(load_locale(language)) == expected, language


def test_locale_files_keep_the_same_placeholders() -> None:
    fallback = load_locale(i18n.DEFAULT_LANGUAGE)
    for language in i18n.SUPPORTED_LANGUAGES:
        locale = load_locale(language)
        mismatched = {
            key: (placeholders(fallback[key]), placeholders(locale[key]))
            for key in fallback
            if placeholders(fallback[key]) != placeholders(locale[key])
        }
        assert mismatched == {}, language


def test_locale_values_are_not_empty() -> None:
    for language in i18n.SUPPORTED_LANGUAGES:
        locale = load_locale(language)
        assert [key for key, value in locale.items() if not value.strip()] == [], language
