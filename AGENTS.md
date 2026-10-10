#### 项目简介

QQ 官方机器人自定义菜单插件。在 AstrBot WebUI 中配置私聊菜单内容, 插件启动时把它们同步到 QQ 官方机器人, 用户在 QQ 私聊界面即可看到自定义菜单。

#### 技术栈

- Python 3.10+(代码里有 X | None、from __future__ import annotations)
- aiohttp(HTTP 客户端, 15s 超时)
- AstrBot Star 插件体系(@register / Context / Star)
- 无第三方数据库, 本地状态仅保存在 AstrBot 配置中

#### 开发命令

不需要，插件通过 AstrBot 加载，测试均需要在运行的 AstrBot 实例下运行。

但是为了规范性，建议使用 Ruff 修复和格式化。

`ruff check . --fix`

`ruff format --check .`

#### 架构约定

1. QQ API 鉴权先 POST `https://bots.qq.com/app/getAppAccessToken` 换取 access_token, 再用 `Authorization: QQBot {token}` 调用 `https://api.bot.qq.com` 下的接口
2. QQ 菜单接口为 `GET /v2/menu` 读取、`PUT /v2/menu` 整表覆盖写入; 菜单项为空时会清空 QQ 上已有的自定义菜单, sync_menu 关闭时只读取不覆盖
3. 每个平台凭证对应一个独立 QQClient, token 缓存在实例内并在过期前 600s 刷新; 外部禁止直接访问 `_` 前缀私有方法
4. 配置解析逻辑整合到 core/config.py 的 helper 函数(get_platforms / get_menu / migrate_menu_config), 不要散落在 main.py
5. 菜单项链接必须归一化为 `https://` 开头(QQ 要求), 由 `_normalize_link` 统一补全, 不要在各处自行拼接
6. 配置使用 template_list, 模板 key 为 send_message / link / menu; 子菜单项通过 parent 字段引用母菜单的名称, 不内嵌
7. 启动时先执行 migrate_menu_config 把旧版 dict 菜单迁移为 template_list 并保存
8. 异步一律 async/await, 不用回调风格
9. 日志统一 from astrbot.api import logger, 前缀 [qq-custom-menu]

#### 代码风格

要点: 类型注解齐全、from __future__ import annotations、`Path` 而非字符串拼路径、`__all__` 导出公开 API。

#### 提交规范

要点: Conventional Commits + 单一职责。

格式: feat: / fix: / refactor: / chore: / docs:
一个 commit/PR 只做一件事
英文 message
分支名 feat/xxx / fix/xxx
