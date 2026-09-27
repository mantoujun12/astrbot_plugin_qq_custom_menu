"""QQ 自定义菜单核心功能。"""

from .config import get_menu, get_platforms
from .menu import MenuSynchronizer

__all__ = ["MenuSynchronizer", "get_menu", "get_platforms"]
