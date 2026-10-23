#### 项目简介

QQ 官方机器人私聊自定义菜单插件。用户在插件可视化视图（Dashboard）中按机器人配置私聊菜单，插件在启动时或手动触发时写入 QQ 官方接口；旧版全局配置保留为「兼容性」入口。

新版机器人配置保存在插件数据目录的 `menu_config.json`；AstrBot 插件配置页（`_conf_schema.json`）继续保存旧版兼容性配置。运行时按 AppID 合并，新版优先接管。

#### 技术栈

- Python 3.10+（代码里有 `X | None`、`from __future__ import annotations`；CI 矩阵为 3.10 / 3.11 / 3.12 / 3.13）
- aiohttp（HTTP 客户端，15s 超时）
- AstrBot Star 插件体系（`@register` / `Context` / `Star`）
- Dashboard：Vue 3 + TypeScript + Vite 8 + Vuetify 4 + vue-router（hash）+ Vitest 5
- 前端工具链要求 Node `^22.12.0 || >=24`（见 `web/dashboard/package.json` 的 `engines`）与 pnpm 9+（lockfile 由 pnpm 12 生成）
- 无第三方数据库，本地状态保存在 AstrBot 的 `data/plugin_data/astrbot_plugin_qq_custom_menu/`

#### 目录结构

```text
main.py                    插件入口：@register、initialize() 启动同步、terminate() 收尾
core/                      插件自身的 Python 包，业务逻辑都在这里
├─ __init__.py             公开 API 汇总（__all__）
├─ config.py               配置解析、菜单归一化、Dashboard 导出 / 校验 / 脱敏 helper
├─ log_stream.py           插件日志环形缓冲、SSE 订阅与日志页数据契约
├─ menu.py                 私聊菜单同步流程与结构化事件
├─ qq_api.py               QQ access_token 与 /v2/menu 客户端
├─ redaction.py            上游响应与日志文本的凭据脱敏 helper
├─ robot_config.py         新版 menu_config.json 读写、校验、导入与运行时合并
├─ state.py                menu_state.yaml 读写、摘要与跨进程锁
├─ sync_runner.py          Dashboard 后台同步任务、SSE 事件缓冲与断线续订
├─ web_api.py              Dashboard Web API（status / config / robots / sync / logs）
├─ paths.py                插件数据目录解析、PLUGIN_NAME / PLUGIN_VERSION
└─ i18n/                   运行期日志翻译（zh-CN / en-US / ru-RU / ja-JP）
_conf_schema.json          WebUI 插件配置 schema
metadata.yaml              插件元数据（版本号唯一来源）
.astrbot-plugin/i18n/      WebUI 侧 i18n（metadata / config / pages.dashboard）
.semgrepignore             安全扫描排除 Vite 生成的 Dashboard 产物，源码仍由 web/dashboard/ 覆盖
web/dashboard/             Dashboard 源码（Vue 3 + TypeScript + Vite + Vuetify + Vitest）
pages/dashboard/           Dashboard 构建产物（提交进仓库的生成文件）
tests/                     离线 pytest 套件（conftest 注入 AstrBot stub）
scripts/                   bump_version.py、package_plugin.py
.github/                   CI、Codecov、Release、Dependabot、Issue 模板
```

#### 开发命令

插件通过 AstrBot 加载，功能性测试仍需要在运行的 AstrBot 实例下进行；业务逻辑与前端可以跑离线测试。

安装运行 + 开发依赖：

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

后端测试与规范检查：

```bash
pytest -q
pytest --cov --cov-branch --cov-report=xml --junitxml=junit.xml -o junit_family=legacy
ruff check . --fix
ruff format --check .
pre-commit run --all-files   # 可选，与 pre-commit.ci / CI 同一套 hooks
```

Dashboard 开发与测试：

```bash
cd web/dashboard
pnpm install
pnpm dev            # 本地 dev server，没有 bridge，走 mock 并显式标注
pnpm build          # vue-tsc + Vite，直接写 pages/dashboard/
pnpm test           # Vitest 单次运行
pnpm test:coverage  # 覆盖率，阈值见 vitest.config.ts
pnpm test:report    # 额外产出 test-report.junit.xml
pnpm test:codecov   # 覆盖率 + JUnit，CI 用的入口
```

打包与版本：

```bash
python scripts/bump_version.py --check   # 校验三处版本号一致
python scripts/bump_version.py minor     # 递增并同步三处版本号
python scripts/bump_version.py --dry-run patch
python scripts/package_plugin.py         # 生成 dist/<插件名>-<版本>.zip
```

#### 架构约定

1. QQ API 鉴权先 POST `https://bots.qq.com/app/getAppAccessToken` 换取 `access_token`，再用 `Authorization: QQBot {token}` 调用 `https://api.bot.qq.com` 下的接口。
2. 插件只处理 C2C 单聊，使用全局 `GET/PUT /v2/menu`；`sync_menu` 关闭时只读取不覆盖。群聊由其他插件负责。
3. 每个平台凭证对应一个独立 `QQClient`，token 缓存在实例内并在过期前 600s 刷新；外部禁止直接访问 `_` 前缀私有方法。
4. 配置解析逻辑整合到 `core/config.py` 的 helper 函数（`get_platforms` / `get_plugin_platforms` / `get_menu` / `migrate_menu_config` / `export_config` / `normalize_config_payload`），不要散落在 `main.py` 或 `web_api.py`。
5. 菜单项链接必须归一化为 `https://` 开头（QQ 要求），由 `_normalize_link` 统一补全；Dashboard 的 `normalizeLink` 必须与它保持一致。
6. 兼容性配置继续使用 `template_list`，模板 key 为 `send_message` / `link` / `switch` / `menu`；新版私聊菜单同样支持这四类。
7. 启动时先执行 `migrate_menu_config` 把旧版 dict 菜单迁移为 `template_list` 并保存；Dashboard 导出的旧式子项也要展开成扁平条目。
8. 异步一律 async/await，不用回调风格；同步流程的进度回调与事件回调也必须是 `Awaitable`。
9. 日志统一 `from astrbot.api import logger`，前缀 `[qq-custom-menu]`；新增运行期文案写入 `core/i18n/*.json`，不要在代码里硬编码中文日志。
10. 运行时数据写入 AstrBot 的 `data/plugin_data/<plugin_name>/`，不得落进仓库；`MenuStateStore` 在写入前自行 `mkdir`。
11. 是否 `PUT` 必须以刚读取到的远端菜单为准：本地摘要可能过期，也可能在 `PUT` 成功后保存失败，不能单独用于跳过同步。
12. Dashboard 的 Web API 统一注册在 `/<plugin_name>/` 下：
    - `GET /status`：本地状态概览，不请求 QQ API
    - `GET|POST /config`：读写插件配置
    - `GET|POST /robots`：读写新版机器人私聊菜单配置
    - `POST /robots/import-legacy`：从兼容配置导入指定 AppID
    - `POST /sync`：触发后台同步，单飞，不排队
    - `GET /sync/events`：SSE 进度流，`since` 用于续订
    - `GET /logs/events`：SSE 日志流，回放最近 1000 条并支持 `since` / `streamId` 续订
13. `ClientSecret` 只能以掩码形式出现在响应、日志和前端；QQ API 错误响应在格式化进异常或日志前必须调用 `core/redaction.py` 脱敏，保存时 `secret` 留空表示沿用同 appid 的已保存密钥，新增平台必须提供密钥。
14. 兼容性平台凭证只读取插件配置中的 `qq_platforms`，不得回退读取 AstrBot 平台配置。
15. `SyncRunner` 负责单飞、事件缓冲与广播：事件带单调递增 `seq`，`stream(since)` 回放后持续推送，收到 `finish` 结束；`start()` 在已有任务运行时返回 `False`。
16. `MenuSynchronizer.sync_all()` 逐平台隔离异常，并发出 `start` / `message`（由调用方映射）/ `platform` / `finish` 事件；任一平台失败不能中止其余平台。
17. i18n 分两条管线：`core/i18n/*.json` 供运行期日志使用；`.astrbot-plugin/i18n/*.json` 供 WebUI 读取，Dashboard 文案放在 `pages.dashboard` 下，`zh-CN`、`en-US`、`ru-RU`、`ja-JP` 四份 locale 的 key 集合与占位符必须一致。面板标题不得直接采用宿主传入的原始视图名 `dashboard`。
18. 版本号只有 `metadata.yaml` 一个来源；`core/paths.py` 的 `PLUGIN_VERSION` 与 `web/dashboard/package.json` 的 `version` 由 `scripts/bump_version.py` 同步，`release.yml` 发布前用 `--check` 校验。
19. `pages/dashboard/` 是生成文件，由 `pnpm build` 写入，不要手工编辑；冲突时重新构建再 `git add`，不要改成 `merge=ours`。`.semgrepignore` 必须继续排除该目录，避免安全扫描把压缩后的 Vuetify 内部 DOM 操作误判为业务代码问题。
20. 测试按模块对应：`core/*.py` → `tests/test_*.py`，Dashboard 源码 → 同目录 `*.test.ts`。公共假件放 `tests/fakes.py` 与 `web/dashboard/src/test/helpers.ts`。
21. `LogBuffer` 只采集插件源码路径产生的日志，环形缓冲容量为 1000；安装时临时启用 DEBUG 并在关闭时恢复 logger 级别，缓冲淘汰后通过 `gap` 事件报告缺口，日志只保存在当前进程内存。日志采集属于可选能力，安装失败不能阻止插件启动；`terminate()` 或构造失败清理必须移除 handler 并结束等待中的 SSE 订阅。

#### Dashboard 数据契约

- `GET /status` 返回 `plugin` / `ready` / `sync_menu` / `platforms`（含 `c2c` 私聊状态）/ `menu` / `robots` / `state`，与 `web/dashboard/src/types/dashboard.ts` 的 `StatusResponse` 对应。
- `GET /config` 返回 `language` / `sync_menu` / `primary_color` / `secondary_color` / `qq_platforms`（掩码）/ `runtime_platforms` / `menu` / `limits`，与 `PluginConfigResponse` 对应。
- `GET /robots` 返回 `version` / `robots` / `available_scenes` / `menu_limits`；`POST /robots` 必须携带当前 `version`，冲突返回 HTTP 409。
- `POST /config` 接受部分字段，后端按字段合并；任一字段校验失败时整次保存被拒绝。
- 状态值：`synced`（摘要与当前菜单一致）、`pending`（摘要不一致）、`unknown`（尚未同步）、`disabled`（`sync_menu` 关闭）。
- 同步事件：`start`（`platforms` / `scenes` / `items`）、`message`（`text`）、`platform`（`pf_id` / `status` / `action` / `saved` / `scenes` / `error`）、`finish`（`ok` / `succeeded` / `failed`）。
- 日志事件：`stream`（`id` / `reset`，连接开始时发送一次）、`log`（`seq` / `timestamp` / `level` / `message` / 可选 `traceback`）、`gap`（`first_seq` / `last_seq` / `count`）、`error`（`code=subscriber_limit`）。

#### 测试与覆盖率

- Python 覆盖率门禁在 `codecov.yml`（flag `unittests`），核心模块目标 90%+。
- Dashboard 覆盖率门禁写在 `vitest.config.ts`（lines 85 / statements 85 / functions 80 / branches 80）。
- Codecov 分两条上传链路：`codecov-core.yml` 与 `codecov-dashboard.yml`，合并后 `after_n_builds: 2`。
- 本地开发没有 bridge 时，Dashboard 使用 `web/dashboard/src/api/mock.ts` 的假数据；保存与同步入口必须显式禁用，不能伪装成功。

#### 代码风格

要点：类型注解齐全、`from __future__ import annotations`、`Path` 而非字符串拼路径、`__all__` 导出公开 API。

- Python 行宽 100，Ruff 规则见 `pyproject.toml`；测试允许 `assert` 与假凭证字符串。
- 前端使用 TypeScript strict 风格，组件测试只断言文本、自有 class、属性与 emit，不断言 Vuetify 内部结构。
- 提交前跑 `ruff check . --fix`、`ruff format --check .` 与 `pre-commit run --all-files`。

#### 文案与标点

- 中文文案（文档、注释、docstring、`zh-CN` i18n、`_conf_schema.json`）统一使用全角标点：`，。：；？！（）“”`；中文句读处不得用半角逗号 `,` 代替 `，`，也不得用半角冒号 `:` 代替 `：`。
- 英文文案、代码、`en-US` locale 文件保持半角标点：`, . : ; ( )`。
- 只调整注释、docstring 与字符串字面量里的标点；代码位置的标点属于语法，不得改动。

#### 提交规范

要点：Conventional Commits + 单一职责。

格式：`feat:` / `fix:` / `refactor:` / `chore:` / `docs:`

- 一个 commit / PR 只做一件事。
- 英文 message。
- 分支名 `feat/xxx` / `fix/xxx` / `chore/xxx` / `docs/xxx`。
- 发布相关提交使用 `chore: release vX.Y.Z`。

#### 变更日志与发布

- `CHANGELOG.md` 使用 Keep a Changelog 结构，未发布改动写在 `## [Unreleased]`。
- `metadata.yaml` 的 `version` 是唯一版本源；推送到 `master` 且该文件变化时，`release.yml` 会校验三处版本号、打包、打 tag 并创建 Release。
- 发布是幂等的：tag 与 release 都已存在时跳过；失败可在 Actions 里手动 `workflow_dispatch` 重跑。
- 发布包只包含 AstrBot 会读取的文件，由 `scripts/package_plugin.py` 统一生成，不要在 workflow 里手工 `cp` / `zip`。
