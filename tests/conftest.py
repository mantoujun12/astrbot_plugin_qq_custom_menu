"""pytest 根配置: 注入 astrbot stub, 使插件代码无需安装 AstrBot 即可导入。

必须先于所有测试模块执行 (pytest 启动时加载 conftest), 因此:
1. 往 sys.modules 注入轻量假 `astrbot` 包;
2. 禁止在此文件 import 任何插件代码 (core.* / main)。

stub 只伪造代码里实际用到的最小接口面:
- astrbot.api.logger            (config / menu 使用)
- astrbot.api.star.Context / Star / register (仅导入期绑定)
- astrbot.core.config.astrbot_config.AstrBotConfig (仅 main.py)

注意：main.py 使用 `from .core import ...` 相对导入，而仓库根不是包。
`tests/test_main.py` 会挂载临时包命名空间，并覆盖装配、初始化与 `_save_config`。
"""

from __future__ import annotations

import importlib
import logging
import sys
import types


def _mod(name: str, **attrs: object) -> types.ModuleType:
    """创建假模块, 设置属性并注册到 sys.modules"""
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    sys.modules[name] = mod
    return mod


def _install_astrbot_stub() -> None:
    """向 sys.modules 注入轻量假 astrbot 包

    已存在真 astrbot (如在 AstrBot 宿主进程内跑 pytest) 时不覆盖。
    """
    if "astrbot" in sys.modules:
        return

    # 真 logging.Logger 而非 Mock: 原生支持 exc_info, 且 pytest caplog 可捕获
    logger = logging.getLogger("astrbot")

    api = _mod("astrbot.api", logger=logger)

    class Context:  # noqa: SM051 - 仅占位, 被测代码只拿它当类型注解
        ...

    class Star:
        """main.py 的基类占位"""

        def __init__(self, context: object = None) -> None:
            self.context = context

    def register(*args: object, **kwargs: object):  # noqa: ANN202 - stub 装饰器
        def deco(cls):
            return cls

        return deco

    _mod(
        "astrbot.api.star",
        Context=Context,
        Star=Star,
        register=register,
    )
    # 父子属性链接, 保证 `import astrbot.api.star` 与
    # `astrbot.api.star.Context` 两种写法都能工作
    api.star = sys.modules["astrbot.api.star"]

    _mod("astrbot.core")
    _mod("astrbot.core.config")
    _mod(
        "astrbot.core.config.astrbot_config",
        AstrBotConfig=type("AstrBotConfig", (dict,), {}),
    )
    # 中间层属性链接, 缺少会导致部分导入路径下 ModuleNotFoundError
    sys.modules["astrbot.core"].config = sys.modules["astrbot.core.config"]

    _mod("astrbot", api=api, core=sys.modules["astrbot.core"])


def _install_aiohttp_stub() -> None:
    """宿主 AstrBot 自带 aiohttp；离线测试缺少时注入最小 stub。

    插件运行期依赖 AstrBot 提供的 aiohttp，不在 requirements.txt 中声明版本，
    避免与宿主自身使用的 aiohttp 版本冲突。
    """
    try:
        importlib.import_module("aiohttp")
    except ModuleNotFoundError:

        class ClientTimeout:
            def __init__(self, *, total: float | None = None, **kwargs: object) -> None:
                self.total = total

        class ClientSession:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

            async def close(self) -> None:
                pass

        _mod("aiohttp", ClientSession=ClientSession, ClientTimeout=ClientTimeout)


_install_astrbot_stub()
_install_aiohttp_stub()
