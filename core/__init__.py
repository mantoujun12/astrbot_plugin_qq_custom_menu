"""QQ 自定义菜单核心功能。"""

from .config import get_menu, get_platforms, migrate_menu_config
from .i18n import initialize as initialize_i18n
from .i18n import t
from .menu import MenuSynchronizer
from .paths import resolve_plugin_data_dir

__all__ = [
    "MenuSynchronizer",
    "get_menu",
    "get_platforms",
    "initialize_i18n",
    "migrate_menu_config",
    "resolve_plugin_data_dir",
    "t",
]
