"""QQ 自定义菜单核心功能。"""

from .config import (
    MENU_LIMITS,
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
from .i18n import initialize as initialize_i18n
from .i18n import t
from .menu import MenuSynchronizer
from .paths import PLUGIN_NAME, PLUGIN_VERSION, resolve_plugin_data_dir
from .sync_runner import SyncRunner
from .web_api import WebApiBundle, build_status, register_web_apis

__all__ = [
    "MENU_LIMITS",
    "MENU_SUB_ITEM_MAX",
    "MENU_TOP_LEVEL_MAX",
    "PLUGIN_NAME",
    "PLUGIN_VERSION",
    "MenuSynchronizer",
    "SyncRunner",
    "WebApiBundle",
    "build_status",
    "export_config",
    "get_menu",
    "get_menu_entries",
    "get_platforms",
    "get_plugin_platforms",
    "initialize_i18n",
    "mask_appid",
    "mask_secret",
    "menu_stats",
    "migrate_menu_config",
    "normalize_config_payload",
    "register_web_apis",
    "resolve_plugin_data_dir",
    "t",
]
