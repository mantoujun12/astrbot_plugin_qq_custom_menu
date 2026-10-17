"""core.config 的单元测试 (纯函数, 无真实 IO/网络)"""

from __future__ import annotations

from typing import Any

from core.config import get_menu, get_platforms, migrate_menu_config
from tests.fakes import FakeContext

# ---------------------------------------------------------------------------
# get_platforms: 插件配置优先 / 回退 AstrBot 全局配置
# ---------------------------------------------------------------------------


def test_get_platforms_prefers_plugin_config() -> None:
    config: dict[str, Any] = {
        "qq_platforms": [
            {"appid": "111", "secret": "s1", "platform": "qq_official"},
        ]
    }
    # 即使 context 里也有平台, 也应优先用插件配置
    context = FakeContext({"platform": [{"type": "qq_official", "appid": "ctx", "secret": "x"}]})
    assert get_platforms(config, context) == [
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
    assert get_platforms(config, FakeContext()) == [
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
    assert get_platforms(config, FakeContext()) == [
        {"appid": "3", "secret": "s", "platform": "qq_official"},
    ]


def test_get_platforms_falls_back_to_context() -> None:
    context = FakeContext(
        {
            "platform": [
                {"type": "qq_official", "appid": "a", "secret": "b"},
                {"type": "aiocqhttp", "appid": "c", "secret": "d"},  # 非 QQ 官方, 应过滤
                {"type": "qq_official_webhook", "appid": "e", "secret": "f"},
            ]
        }
    )
    assert get_platforms({}, context) == [
        {"appid": "a", "secret": "b", "platform": "qq_official"},
        {"appid": "e", "secret": "f", "platform": "qq_official_webhook"},
    ]


def test_get_platforms_non_list_config_falls_back() -> None:
    context = FakeContext({"platform": [{"type": "qq_official", "appid": "a", "secret": "b"}]})
    assert get_platforms({"qq_platforms": "oops"}, context) == [
        {"appid": "a", "secret": "b", "platform": "qq_official"},
    ]


def test_get_platforms_empty_everywhere() -> None:
    assert get_platforms({}, FakeContext()) == []


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
