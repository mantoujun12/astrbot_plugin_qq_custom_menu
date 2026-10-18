"""core.robot_config 的单元测试。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.robot_config import (
    MENU_CONFIG_FILENAME,
    MenuConfigError,
    build_runtime_robots,
    empty_menu_config,
    export_menu_config,
    legacy_to_robot_drafts,
    load_menu_config,
    robot_item_counts,
    save_menu_config,
    validate_menu_config,
)


def robot_payload(
    *,
    appid: str = "app-new",
    secret: str = "new-secret",
    robot_id: str = "robot-1",
) -> dict[str, Any]:
    return {
        "id": robot_id,
        "name": "主机器人",
        "appid": appid,
        "secret": secret,
        "platform": "qq_official",
        "scenes": {
            "c2c": {
                "enabled": True,
                "items": [
                    {"type": "send_message", "name": "帮助", "message": "/help", "parent": ""},
                    {
                        "type": "switch",
                        "name": "联网",
                        "switch_id": "search",
                        "default": True,
                        "parent": "",
                    },
                ],
            },
        },
    }


def test_missing_config_returns_empty(tmp_path: Path) -> None:
    assert load_menu_config(tmp_path) == {"version": 1, "robots": []}


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    payload = {"version": 3, "robots": [robot_payload()]}

    path = save_menu_config(tmp_path, payload)

    assert path == tmp_path / MENU_CONFIG_FILENAME
    assert load_menu_config(tmp_path) == payload


def test_invalid_json_and_shape_raise(tmp_path: Path) -> None:
    path = tmp_path / MENU_CONFIG_FILENAME
    path.write_text("{", encoding="utf-8")
    with pytest.raises(MenuConfigError):
        load_menu_config(tmp_path)

    path.write_text(json.dumps({"version": 0, "robots": []}), encoding="utf-8")
    with pytest.raises(MenuConfigError):
        load_menu_config(tmp_path)

    path.write_text(json.dumps({"version": 1, "robots": {}}), encoding="utf-8")
    with pytest.raises(MenuConfigError):
        load_menu_config(tmp_path)


def test_validate_normalizes_and_keeps_existing_secret() -> None:
    existing = {"version": 1, "robots": [robot_payload()]}
    payload = {
        "robots": [
            {
                "id": "robot-1",
                "name": " 主机器人 ",
                "appid": "app-new",
                "secret": "",
                "platform": "qq_official",
                "scenes": {
                    "c2c": {
                        "enabled": True,
                        "items": [
                            {
                                "type": "link",
                                "name": " 官网 ",
                                "link": "http://example.com",
                                "parent": "",
                            }
                        ],
                    },
                },
            }
        ]
    }

    normalized, errors = validate_menu_config(existing, payload)

    assert errors == []
    robot = normalized["robots"][0]
    assert robot["name"] == "主机器人"
    assert robot["secret"] == "new-secret"
    assert robot["scenes"]["c2c"]["items"] == [
        {
            "__template_key": "link",
            "name": "官网",
            "link": "https://example.com",
            "parent": "",
        }
    ]


def test_validate_rejects_duplicate_appid() -> None:
    first = robot_payload()
    second = robot_payload(robot_id="robot-2")

    _, errors = validate_menu_config(
        empty_menu_config(),
        {"robots": [first, second]},
    )

    assert errors
    assert any("AppID" in error for error in errors)


def test_export_masks_secret_and_expands_editor_items() -> None:
    config = {
        "version": 2,
        "robots": [
            {
                **robot_payload(secret="abcdef123456"),
                "scenes": {
                    "c2c": {
                        "enabled": True,
                        "items": [
                            {
                                "type": "menu",
                                "name": "更多",
                                "sub_menu_items": [
                                    {
                                        "type": "link",
                                        "name": "文档",
                                        "link": "https://docs.app",
                                    }
                                ],
                            }
                        ],
                    },
                },
            }
        ],
    }

    exported = export_menu_config(config)

    assert exported["version"] == 2
    assert exported["available_scenes"] == ["c2c"]
    assert exported["robots"][0]["secret_masked"] == "ab********56"
    assert exported["robots"][0]["secret_set"] is True
    assert exported["robots"][0]["scenes"]["c2c"]["items"] == [
        {"type": "menu", "name": "更多", "parent": ""},
        {
            "type": "link",
            "name": "文档",
            "parent": "更多",
            "link": "https://docs.app",
        },
    ]


def test_build_runtime_robots_new_config_takes_precedence_by_appid() -> None:
    legacy_config = {
        "menu": [
            {"type": "send_message", "name": "旧帮助", "message": "/old"},
        ]
    }
    legacy_platforms = [
        {"appid": "app-new", "secret": "legacy-secret", "platform": "qq_official"},
        {"appid": "app-old", "secret": "old-secret", "platform": "qq_official"},
    ]
    new_config = {"version": 1, "robots": [robot_payload()]}

    runtime = build_runtime_robots(legacy_config, new_config, legacy_platforms)

    assert [robot["appid"] for robot in runtime] == ["app-new", "app-old"]
    assert runtime[0]["source"] == "robot"
    assert runtime[1]["source"] == "compatibility"
    assert runtime[1]["scenes"]["c2c"]["items"][0]["name"] == "旧帮助"


def test_legacy_import_and_counts() -> None:
    legacy_config = {
        "menu": [
            {"type": "send_message", "name": "帮助", "message": "/help"},
        ]
    }
    platforms = [
        {"appid": "app-old", "secret": "secret", "platform": "qq_official"},
    ]

    drafts = legacy_to_robot_drafts(legacy_config, platforms, ["app-old"])
    config = {"version": 1, "robots": [robot_payload(), drafts[0]]}
    counts = robot_item_counts(config)

    assert drafts[0]["appid"] == "app-old"
    assert drafts[0]["scenes"]["c2c"]["enabled"] is True
    assert counts == {
        "robots": 2,
        "c2c_items": 3,
        "c2c_top_level": 3,
        "c2c_sub_items": 0,
    }


def test_validate_rejects_invalid_payload_shapes() -> None:
    assert validate_menu_config({}, [])[1]
    assert validate_menu_config({}, {"robots": "bad"})[1]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda robot: robot.update(appid=""),
        lambda robot: robot.update(name=""),
        lambda robot: robot.update(name="x" * 65),
        lambda robot: robot.update(platform="bad"),
        lambda robot: robot.update(secret=""),
        lambda robot: robot.update(scenes="bad"),
    ],
)
def test_validate_reports_robot_field_errors(mutate: Any) -> None:
    raw = robot_payload()
    mutate(raw)

    normalized, errors = validate_menu_config(
        empty_menu_config(),
        {"robots": [raw]},
    )

    assert normalized["robots"] == []
    assert errors


def test_validate_reports_non_object_and_duplicate_ids() -> None:
    first = robot_payload()
    second = robot_payload(appid="other", robot_id="robot-1")
    _, errors = validate_menu_config(
        empty_menu_config(),
        {"robots": ["bad", first, second]},
    )
    assert any("对象" in error for error in errors)
    assert any("ID" in error for error in errors)


def test_validate_reports_invalid_private_menu_items() -> None:
    invalid_cases = [
        {"type": "unknown", "name": "不支持"},
        {"type": "link", "name": "链接", "link": ""},
    ]
    for item in invalid_cases:
        raw = robot_payload()
        raw["scenes"]["c2c"]["items"] = [item]
        _, current_errors = validate_menu_config({}, {"robots": [raw]})
        assert current_errors


def test_load_rejects_non_object_and_save_failure(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    path = tmp_path / MENU_CONFIG_FILENAME
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(MenuConfigError):
        load_menu_config(tmp_path)

    def fail_replace(self: Path, target: Path) -> Path:
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(MenuConfigError):
        save_menu_config(tmp_path, empty_menu_config())


def test_export_and_import_skip_invalid_entries() -> None:
    exported = export_menu_config(
        {
            "version": 0,
            "robots": [
                "bad",
                {"appid": ""},
                {
                    "id": "r1",
                    "name": "机器人",
                    "appid": "app",
                    "platform": "qq_official",
                    "scenes": {
                        "c2c": {"enabled": False, "items": "bad"},
                    },
                },
            ],
        }
    )
    assert exported["version"] == 1
    assert exported["robots"][0]["scenes"]["c2c"]["items"] == []

    drafts = legacy_to_robot_drafts(
        {"menu": []},
        [
            {"appid": "missing", "platform": "qq_official"},
            {"appid": "other", "secret": "secret", "platform": "qq_official"},
        ],
        ["wanted"],
    )
    assert drafts == []
