"""core.config 的单元测试 (纯函数, 无真实 IO/网络)"""

from __future__ import annotations

from typing import Any

from core.config import (
    MENU_SUB_ITEM_MAX,
    MENU_TOP_LEVEL_MAX,
    export_config,
    get_menu,
    get_menu_entries,
    get_platforms,
    get_plugin_platforms,
    mask_appid,
    mask_secret,
    menu_stats,
    migrate_menu_config,
    normalize_config_payload,
)

# ---------------------------------------------------------------------------
# get_platforms: 只读取插件配置
# ---------------------------------------------------------------------------


def test_get_platforms_reads_plugin_config() -> None:
    config: dict[str, Any] = {
        "qq_platforms": [
            {"appid": "111", "secret": "s1", "platform": "qq_official"},
        ]
    }
    assert get_platforms(config) == [
        {"appid": "111", "secret": "s1", "platform": "qq_official"},
    ]


def test_get_platforms_defaults_and_type_alias() -> None:
    config: dict[str, Any] = {
        "qq_platforms": [
            # 缺 platform 时读 type, 再缺则默认 qq_official
            {"appid": "1", "secret": "s", "type": "qq_official_webhook"},
            {"appid": "2", "secret": "s"},
        ]
    }
    assert get_platforms(config) == [
        {"appid": "1", "secret": "s", "platform": "qq_official_webhook"},
        {"appid": "2", "secret": "s", "platform": "qq_official"},
    ]


def test_get_platforms_skips_disabled_and_incomplete() -> None:
    config: dict[str, Any] = {
        "qq_platforms": [
            {"appid": "1", "secret": "s", "enable": False},  # 显式禁用
            {"appid": "2"},  # 缺 secret
            {"secret": "s"},  # 缺 appid
            "not a dict",
            {"appid": "3", "secret": "s"},  # 有效
        ]
    }
    assert get_platforms(config) == [
        {"appid": "3", "secret": "s", "platform": "qq_official"},
    ]


def test_get_platforms_invalid_config_is_empty() -> None:
    assert get_platforms({"qq_platforms": "oops"}) == []


def test_get_platforms_empty_config_is_empty() -> None:
    assert get_platforms({}) == []


# ---------------------------------------------------------------------------
# get_menu: 菜单项归一化 / 链接补全 / parent 组装
# ---------------------------------------------------------------------------


def test_get_menu_send_message_and_link() -> None:
    config: dict[str, Any] = {
        "menu": [
            {"__template_key": "send_message", "name": "帮助", "message": "/help"},
            {"__template_key": "link", "name": "官网", "link": "example.com"},
        ]
    }
    assert get_menu(config) == {
        "items": [
            {"type": "send_message", "name": "帮助", "send_message": "/help"},
            {"type": "link", "name": "官网", "link": "https://example.com"},
        ]
    }


def test_get_menu_link_normalization() -> None:
    config: dict[str, Any] = {
        "menu": [
            {"type": "link", "name": "a", "link": "http://a.com"},
            {"type": "link", "name": "b", "link": "//b.com"},
            {"type": "link", "name": "c", "link": "https://c.com"},
            {"type": "link", "name": "d", "link": "  spaced.com  "},
        ]
    }
    items = get_menu(config)["items"]
    assert [item["link"] for item in items] == [
        "https://a.com",
        "https://b.com",
        "https://c.com",
        "https://spaced.com",
    ]


def test_get_menu_switch_item() -> None:
    config: dict[str, Any] = {
        "menu": [
            {
                "type": "switch",
                "name": "联网",
                "switch_id": "search",
                "default": True,
            }
        ]
    }
    assert get_menu(config) == {
        "items": [
            {
                "type": "switch",
                "name": "联网",
                "switch": {"switch_id": "search", "default": True},
            }
        ]
    }


def test_get_menu_builds_children_from_parent() -> None:
    config: dict[str, Any] = {
        "menu": [
            {"type": "menu", "name": "更多"},
            {"type": "send_message", "name": "关于", "send_message": "/about", "parent": "更多"},
            {"type": "link", "name": "文档", "link": "docs.app", "parent": "更多"},
        ]
    }
    assert get_menu(config) == {
        "items": [
            {
                "type": "menu",
                "name": "更多",
                "sub_menu_items": [
                    {"type": "send_message", "name": "关于", "send_message": "/about"},
                    {"type": "link", "name": "文档", "link": "https://docs.app"},
                ],
            }
        ]
    }


def test_get_menu_legacy_nested_sub_menu_items() -> None:
    config: dict[str, Any] = {
        "menu": [
            {
                "type": "menu",
                "name": "更多",
                "sub_menu_items": [
                    {"type": "send_message", "name": "关于", "send_message": "/about"},
                    {"type": "menu", "name": "非法子菜单"},  # 子项不允许 menu 类型
                ],
            }
        ]
    }
    assert get_menu(config) == {
        "items": [
            {
                "type": "menu",
                "name": "更多",
                "sub_menu_items": [
                    {"type": "send_message", "name": "关于", "send_message": "/about"},
                ],
            }
        ]
    }


def test_get_menu_unmatched_parent_ignored(caplog: Any) -> None:
    config: dict[str, Any] = {
        "menu": [
            {"type": "send_message", "name": "孤儿", "send_message": "/x", "parent": "不存在"},
        ]
    }
    assert get_menu(config) == {"items": []}
    assert "不存在" in caplog.text


def test_get_menu_skips_invalid_entries() -> None:
    config: dict[str, Any] = {
        "menu": [
            "not a dict",
            {"type": "unknown", "name": "x"},
            {"type": "send_message", "name": ""},
            {"type": "send_message", "name": "无消息"},
            {"type": "link", "name": "空链接", "link": "   "},
            {"type": "send_message", "name": " 有效 ", "send_message": "/ok"},
        ]
    }
    assert get_menu(config) == {
        "items": [{"type": "send_message", "name": "有效", "send_message": "/ok"}],
    }


def test_get_menu_legacy_dict_shape() -> None:
    config: dict[str, Any] = {
        "menu": {"items": [{"type": "send_message", "name": "旧", "send_message": "/old"}]}
    }
    assert get_menu(config) == {
        "items": [{"type": "send_message", "name": "旧", "send_message": "/old"}],
    }


def test_get_menu_empty_configs() -> None:
    assert get_menu({}) == {"items": []}
    assert get_menu({"menu": "oops"}) == {"items": []}
    assert get_menu({"menu": {"items": "oops"}}) == {"items": []}


# ---------------------------------------------------------------------------
# migrate_menu_config: 旧版 dict -> template_list
# ---------------------------------------------------------------------------


class _SaveableDict(dict):
    """可记录 save_config 调用的 dict, 模拟 AstrBotConfig"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.saved = 0

    def save_config(self) -> None:
        self.saved += 1


def test_migrate_menu_config_from_legacy() -> None:
    config = _SaveableDict(
        {
            "menu": {
                "items": [
                    {"type": "send_message", "name": "帮助", "send_message": "/help"},
                    {
                        "type": "menu",
                        "name": "更多",
                        "sub_menu_items": [
                            {"type": "link", "name": "文档", "link": "docs.app"},
                        ],
                    },
                ]
            }
        }
    )
    assert migrate_menu_config(config) is True
    assert config["menu"] == [
        {"__template_key": "send_message", "name": "帮助", "message": "/help", "parent": ""},
        {"__template_key": "menu", "name": "更多"},
        {"__template_key": "link", "name": "文档", "link": "docs.app", "parent": "更多"},
    ]
    assert config.saved == 1


def test_migrate_menu_config_non_dict_returns_false() -> None:
    config = _SaveableDict({"menu": [{"type": "send_message"}]})
    assert migrate_menu_config(config) is False
    assert config.saved == 0


def test_migrate_menu_config_without_items() -> None:
    config = _SaveableDict({"menu": {}})
    assert migrate_menu_config(config) is True
    assert config["menu"] == []
    assert config.saved == 1


def test_migrate_menu_config_skips_invalid_entries() -> None:
    config = _SaveableDict(
        {
            "menu": {
                "items": [
                    "not a dict",
                    {"type": "send_message", "name": ""},  # 空名称
                    {"type": "menu", "name": "  "},  # 空名称的母菜单
                    {"type": "link", "name": "无链接"},  # link 字段缺失
                    {"type": "send_message", "name": "保留", "send_message": "/keep"},
                ]
            }
        }
    )
    assert migrate_menu_config(config) is True
    assert config["menu"] == [
        {"__template_key": "send_message", "name": "保留", "message": "/keep", "parent": ""},
    ]


# ---------------------------------------------------------------------------
# 覆盖率补充分支：非法字段 / 旧格式边界
# ---------------------------------------------------------------------------


def test_get_menu_link_non_string_is_skipped() -> None:
    config: dict[str, Any] = {"menu": [{"type": "link", "name": "坏链接", "link": 123}]}
    assert get_menu(config) == {"items": []}


def test_get_menu_menu_children_non_list_is_ignored() -> None:
    config: dict[str, Any] = {"menu": [{"type": "menu", "name": "更多", "sub_menu_items": "oops"}]}
    assert get_menu(config) == {"items": [{"type": "menu", "name": "更多", "sub_menu_items": []}]}


def test_migrate_menu_config_non_list_items() -> None:
    config = _SaveableDict({"menu": {"items": "oops"}})
    assert migrate_menu_config(config) is True
    assert config["menu"] == []
    assert config.saved == 1


def test_migrate_menu_config_without_save_config() -> None:
    config: dict[str, Any] = {
        "menu": {"items": [{"type": "send_message", "name": "保留", "send_message": "/keep"}]}
    }
    assert migrate_menu_config(config) is True
    assert config["menu"] == [
        {"__template_key": "send_message", "name": "保留", "message": "/keep", "parent": ""}
    ]


def test_migrate_menu_config_skips_invalid_children() -> None:
    config = _SaveableDict(
        {
            "menu": {
                "items": [
                    {
                        "type": "menu",
                        "name": "更多",
                        "sub_menu_items": [
                            "not a dict",
                            {"type": "send_message", "name": "关于", "send_message": "/about"},
                        ],
                    },
                    {"type": "menu", "name": "无子项", "sub_menu_items": "oops"},
                ]
            }
        }
    )
    assert migrate_menu_config(config) is True
    assert config["menu"] == [
        {"__template_key": "menu", "name": "更多"},
        {"__template_key": "send_message", "name": "关于", "message": "/about", "parent": "更多"},
        {"__template_key": "menu", "name": "无子项"},
    ]


# ---------------------------------------------------------------------------
# Dashboard 配置读写：导出、统计、脱敏与提交校验
# ---------------------------------------------------------------------------


def test_mask_helpers() -> None:
    assert mask_appid("123456789") == "123****89"
    assert mask_appid("short") == "*****"
    assert mask_appid(None) == ""
    assert mask_secret("abcdef123456") == "ab********56"
    assert mask_secret("tiny") == "****"
    assert mask_secret(None) == ""


def test_get_plugin_platforms_does_not_fall_back() -> None:
    config: dict[str, Any] = {
        "qq_platforms": [
            {"appid": "1", "secret": "s", "platform": "qq_official"},
            {"appid": "2"},
            "invalid",
        ]
    }
    assert get_plugin_platforms(config) == [
        {"appid": "1", "secret": "s", "platform": "qq_official"},
    ]
    assert get_plugin_platforms({}) == []


def test_get_menu_entries_flattens_legacy_children() -> None:
    config: dict[str, Any] = {
        "menu": [
            {
                "type": "menu",
                "name": "更多",
                "sub_menu_items": [
                    {"type": "send_message", "name": "关于", "send_message": "/about"},
                ],
            },
            {"type": "link", "name": "官网", "link": "example.com"},
        ]
    }
    assert get_menu_entries(config) == [
        {"type": "menu", "name": "更多", "parent": ""},
        {"type": "send_message", "name": "关于", "parent": "更多", "message": "/about"},
        {"type": "link", "name": "官网", "parent": "", "link": "https://example.com"},
    ]


def test_get_menu_entries_keeps_flat_children() -> None:
    config: dict[str, Any] = {
        "menu": [
            {"type": "menu", "name": "更多"},
            {"type": "send_message", "name": "关于", "message": "/about", "parent": "更多"},
        ]
    }
    assert get_menu_entries(config) == [
        {"type": "menu", "name": "更多", "parent": ""},
        {"type": "send_message", "name": "关于", "parent": "更多", "message": "/about"},
    ]


def test_menu_stats_counts_top_level_and_children() -> None:
    config: dict[str, Any] = {
        "menu": [
            {"type": "menu", "name": "更多"},
            {"type": "send_message", "name": "关于", "message": "/about", "parent": "更多"},
            {"type": "link", "name": "官网", "link": "example.com"},
        ]
    }
    assert menu_stats(config) == {
        "top_level": 2,
        "sub_items": 1,
        "total": 3,
        "top_level_max": MENU_TOP_LEVEL_MAX,
        "sub_items_max": MENU_SUB_ITEM_MAX,
    }


def test_export_config_masks_secrets_and_expands_menu() -> None:
    config: dict[str, Any] = {
        "language": "en-US",
        "sync_menu": False,
        "qq_platforms": [
            {"appid": "123456789", "secret": "abcdef123456", "platform": "qq_official"},
        ],
        "menu": [
            {"type": "send_message", "name": "帮助", "send_message": "/help"},
            {
                "type": "menu",
                "name": "更多",
                "sub_menu_items": [
                    {"type": "link", "name": "文档", "link": "docs.app"},
                ],
            },
        ],
    }
    payload = export_config(config)

    assert payload["language"] == "en-US"
    assert payload["sync_menu"] is False
    assert payload["qq_platforms"] == [
        {
            "appid": "123456789",
            "platform": "qq_official",
            "secret_masked": "ab********56",
            "secret_set": True,
        }
    ]
    assert payload["menu"] == [
        {"type": "send_message", "name": "帮助", "parent": "", "message": "/help"},
        {"type": "menu", "name": "更多", "parent": ""},
        {"type": "link", "name": "文档", "parent": "更多", "link": "https://docs.app"},
    ]
    assert payload["limits"] == {
        "top_level_max": MENU_TOP_LEVEL_MAX,
        "sub_items_max": MENU_SUB_ITEM_MAX,
    }


def test_export_config_masks_runtime_platforms() -> None:
    runtime = [{"appid": "abc", "secret": "secret", "platform": "qq_official"}]
    payload = export_config({}, runtime)

    assert payload["language"] == "zh-CN"
    assert payload["sync_menu"] is True
    assert payload["qq_platforms"] == []
    assert payload["runtime_platforms"] == [
        {
            "pf_id": "***",
            "appid": "***",
            "platform": "qq_official",
            "secret_set": True,
            "source": "plugin",
        }
    ]


def test_export_config_skips_invalid_platform_entries() -> None:
    config: dict[str, Any] = {"qq_platforms": ["invalid", {"appid": "a"}]}
    payload = export_config(config)
    assert payload["qq_platforms"] == [
        {
            "appid": "a",
            "platform": "qq_official",
            "secret_masked": "",
            "secret_set": False,
        }
    ]


def test_normalize_config_payload_keeps_partial_fields() -> None:
    existing: dict[str, Any] = {
        "qq_platforms": [
            {"appid": "a", "secret": "old-secret", "platform": "qq_official"},
        ]
    }
    payload: dict[str, Any] = {
        "language": "en-US",
        "sync_menu": False,
        "qq_platforms": [
            {"appid": "a", "secret": "", "platform": "qq_official"},
            {"appid": "b", "secret": "new-secret", "platform": "qq_official_webhook"},
        ],
        "menu": [
            {"type": "menu", "name": "更多"},
            {"type": "send_message", "name": "关于", "message": " /about ", "parent": "更多"},
            {"type": "link", "name": "文档", "link": "docs.app", "parent": "更多"},
            {"type": "link", "name": "官网", "link": "example.com"},
        ],
    }

    values, errors = normalize_config_payload(existing, payload)

    assert errors == []
    assert values["language"] == "en-US"
    assert values["sync_menu"] is False
    assert values["qq_platforms"] == [
        {
            "__template_key": "qq_platform",
            "appid": "a",
            "secret": "old-secret",
            "platform": "qq_official",
        },
        {
            "__template_key": "qq_platform",
            "appid": "b",
            "secret": "new-secret",
            "platform": "qq_official_webhook",
        },
    ]
    assert values["menu"] == [
        {"__template_key": "menu", "name": "更多"},
        {"__template_key": "send_message", "name": "关于", "message": "/about", "parent": "更多"},
        {"__template_key": "link", "name": "文档", "link": "https://docs.app", "parent": "更多"},
        {"__template_key": "link", "name": "官网", "link": "https://example.com", "parent": ""},
    ]


def test_normalize_config_payload_rejects_invalid_language_and_sync_menu() -> None:
    values, errors = normalize_config_payload({}, {"language": "fr-FR", "sync_menu": "yes"})
    assert len(errors) == 2
    assert "language" not in values
    assert "sync_menu" not in values


def test_normalize_config_payload_rejects_invalid_platforms() -> None:
    cases: list[Any] = [
        "oops",
        ["oops"],
        [{"appid": ""}],
        [{"appid": "a", "secret": "s"}, {"appid": "a", "secret": "s"}],
        [{"appid": "a", "secret": "s", "platform": "bad"}],
        [{"appid": "a", "secret": ""}],
    ]
    # 错误文案跟随当前语言，这里只断言确实失败且没有写出字段
    for platforms in cases:
        values, errors = normalize_config_payload({}, {"qq_platforms": platforms})
        assert errors, platforms
        assert "qq_platforms" not in values


def test_normalize_config_payload_rejects_invalid_menu() -> None:
    cases: list[Any] = [
        "oops",
        ["oops"],
        [{"type": "bad", "name": "x"}],
        [{"type": "send_message", "name": ""}],
        [{"type": "send_message", "name": "无消息"}],
        [{"type": "link", "name": "无链接", "link": "   "}],
        [{"type": "link", "name": "坏链接", "link": 123}],
        [{"type": "menu", "name": "子菜单", "parent": "父"}],
        [{"type": "send_message", "name": "孤儿", "message": "/x", "parent": "不存在"}],
        [
            {"type": "menu", "name": "更多"},
            *[
                {
                    "type": "send_message",
                    "name": f"子项{index}",
                    "message": "/x",
                    "parent": "更多",
                }
                for index in range(MENU_SUB_ITEM_MAX + 1)
            ],
        ],
    ]
    for menu in cases:
        values, errors = normalize_config_payload({}, {"menu": menu})
        assert errors, menu
        assert "menu" not in values


def test_normalize_config_payload_rejects_top_level_limit_and_duplicates() -> None:
    too_many = [
        {"type": "send_message", "name": f"菜单{index}", "message": "/x"}
        for index in range(MENU_TOP_LEVEL_MAX + 1)
    ]
    values, errors = normalize_config_payload({}, {"menu": too_many})
    assert errors
    assert "menu" not in values

    duplicated = [
        {"type": "send_message", "name": "重复", "message": "/x"},
        {"type": "link", "name": "重复", "link": "example.com"},
    ]
    values, errors = normalize_config_payload({}, {"menu": duplicated})
    assert errors
    assert "menu" not in values


def test_normalize_config_payload_validates_switch_ids() -> None:
    values, missing = normalize_config_payload(
        {},
        {"menu": [{"type": "switch", "name": "联网", "switch_id": "", "parent": ""}]},
    )
    assert missing
    assert "menu" not in values

    values, duplicate = normalize_config_payload(
        {},
        {
            "menu": [
                {"type": "switch", "name": "联网", "switch_id": "same", "parent": ""},
                {"type": "switch", "name": "搜索", "switch_id": "same", "parent": ""},
            ]
        },
    )
    assert duplicate
    assert "menu" not in values
