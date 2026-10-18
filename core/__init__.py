"""QQ 自定义菜单核心功能。"""

from .config import (
    MENU_LIMITS,
    MENU_SUB_ITEM_MAX,
    MENU_TOP_LEVEL_MAX,
    SCENE_C2C,
    SCENES,
    export_config,
    get_menu,
    get_menu_entries,
    get_platforms,
    get_plugin_platforms,
    mask_appid,
    mask_secret,
    menu_from_entries,
    menu_stats,
    migrate_menu_config,
    normalize_config_payload,
)
from .i18n import initialize as initialize_i18n
from .i18n import t
from .menu import MenuSynchronizer
from .paths import PLUGIN_NAME, PLUGIN_VERSION, resolve_plugin_data_dir
from .robot_config import (
    MENU_CONFIG_FILENAME,
    MenuConfigError,
    build_runtime_robots,
    export_menu_config,
    load_menu_config,
    robot_item_counts,
    save_menu_config,
    validate_menu_config,
)
from .sync_runner import SyncRunner
from .web_api import WebApiBundle, build_status, register_web_apis

__all__ = [
    "MENU_LIMITS",
    "MENU_SUB_ITEM_MAX",
    "MENU_TOP_LEVEL_MAX",
    "MENU_CONFIG_FILENAME",
    "MenuConfigError",
    "PLUGIN_NAME",
    "PLUGIN_VERSION",
    "SCENE_C2C",
    "SCENES",
    "MenuSynchronizer",
    "SyncRunner",
    "WebApiBundle",
    "build_status",
    "build_runtime_robots",
    "export_config",
    "export_menu_config",
    "get_menu",
    "get_menu_entries",
    "get_platforms",
    "get_plugin_platforms",
    "initialize_i18n",
    "load_menu_config",
    "mask_appid",
    "mask_secret",
    "menu_from_entries",
    "menu_stats",
    "migrate_menu_config",
    "normalize_config_payload",
    "register_web_apis",
    "resolve_plugin_data_dir",
    "robot_item_counts",
    "save_menu_config",
    "t",
    "validate_menu_config",
]
