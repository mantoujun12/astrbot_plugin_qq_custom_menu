# Changelog

本文件记录本项目的所有重要变更。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/),
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增

- Dashboard 新增「机器人」页：按机器人独立维护私聊自定义菜单，支持从兼容配置按 AppID 导入
- 新增 `core/robot_config.py` 与运行时数据文件 `menu_config.json`，包含机器人 ID、凭证、平台类型、场景启停与版本并发校验
- 私聊菜单新增 QQ「开关」类型
- 新增「兼容性」页，集中维护旧版全局 `qq_platforms` 与私聊 `menu`
- 新增 `codecov.yml`，按 `unittests`（Python）与 `dashboard`（前端）两个 flag 分别设置覆盖率门禁与评论
- 新增 `.gitattributes`，把前端构建产物标记为生成文件并使用 `merge=binary`，同时统一文本文件的 LF 换行
- CI 拆分为 lint / Pytest 矩阵（`ci.yml`）与覆盖率上传（`codecov-core.yml`），覆盖率任务同时上传 XML 与 JUnit 测试报告
- 新增插件可视化视图（Dashboard）：状态概览、菜单配置、机器人凭证、设置四个页面，支持保存配置、保存并同步与 SSE 实时同步进度
- 新增 `core/web_api.py`：注册状态、配置读写、同步入口与同步事件流接口，`secret` 只返回掩码
- 新增 `core/sync_runner.py`：后台单飞同步任务、事件缓冲与断线续订（`since`）
- 新增 `web/dashboard/`（Vue 3 + Vite 8 + Vuetify 4 + Vitest）与构建产物 `pages/dashboard/`
- 新增 Dashboard CI（`ci-dashboard.yml`）与 Codecov（`codecov-dashboard.yml`），并在 Dependabot 中接管前端依赖
- 新增 `scripts/package_plugin.py`：只收录 AstrBot 会读取的文件，固定时间戳生成可复现 zip
- 新增 `scripts/bump_version.py`：同步 `metadata.yaml` / `core/paths.py` / `web/dashboard/package.json` 三处版本号，支持 `--check` / `--dry-run` / `--force` 与交互式选择

### 变更

- 新旧配置按 AppID 合并，新版配置优先接管；兼容配置继续覆盖未被接管的历史机器人
- 同步状态与进度细化到机器人
- 子菜单上限按 QQ 当前接口调整为 5 项
- `core/menu.py` 增加结构化同步事件与逐平台失败隔离，Dashboard 可展示每个平台的同步结果
- `main.py` 注册视图 Web API、暴露配置保存回调，并使用 `core/paths.py` 的 `PLUGIN_VERSION` 作为唯一版本来源
- `core/config.py` 增加 Dashboard 配置导出、菜单统计、脱敏与提交校验 helper
- `release.yml` 改用 `scripts/bump_version.py --check` 校验版本、`scripts/package_plugin.py` 打包，并把发布流程改为幂等（tag / release 已存在时跳过）

### 修复

- 兼容性配置为空时不再回退读取并同步 AstrBot 平台配置中的 QQ 官方机器人

### 文档

- 更新 README / metadata：插件仅处理私聊自定义菜单，群聊功能由其他插件负责
- 重写 README：补充 Dashboard、配置说明、同步行为、开发测试、打包发布、CI / Codecov 与目录结构
- 扩充 AGENTS.md：补齐 Dashboard 架构约定、数据契约、测试覆盖率、版本与发布流程

### 测试

- 新增机器人配置、兼容导入、版本冲突、Dashboard 新页面与 i18n 根键对账测试
- 新增 `tests/test_main.py`，覆盖插件装配、初始化同步、异常兜底与资源释放
- 补充 `core/config.py`、`core/i18n.py`、`core/paths.py`、`core/state.py` 的边界分支测试，Python 行覆盖率提升到 99%
- 新增 `tests/test_web_api.py`、`tests/test_sync_runner.py` 与菜单同步事件测试，Python 行覆盖率保持 99%
- 新增 24 个 Vitest 测试文件，前端行覆盖率约 94%，并在 `vitest.config.ts` 中设置覆盖率硬门
- 新增 `tests/test_package_script.py` 与 `tests/test_bump_script.py`，覆盖打包内容、可复现性、版本号解析 / 写回 / 校验与交互式流程

## [v0.2.3] - 2026-10-12

### 变更

- 将 `aiohttp` 依赖要求由 `>=3.14.4` 调整为精确锁定 `==3.14.3`, 避免自动更新引入不兼容版本 (#12)

## [v0.2.2] - 2026-10-11

### 新增

- 基于 AstrBot stub 的离线 pytest 测试套件, 覆盖 `config` / `menu` / `qq_api` 等业务逻辑, 无需安装 AstrBot 即可运行 (#10)
- GitHub Actions CI, 在 Python 3.10 - 3.13 矩阵上运行测试并上传覆盖率报告 (#10)
- 与 CI 保持一致的 pre-commit hooks, 统一执行 ruff check + format 及通用文件检查 (#10)
- 新增 Dependabot 依赖自动更新配置
- 新增 bug report / feature request issue 模板
- 新增 AGENTS.md, 沉淀开发命令与架构约定
- 拆分 `requirements.txt` / `requirements-dev.txt`, 区分运行时与开发依赖

### 变更

- 将 `aiohttp` 依赖要求更新为 `>=3.14.4` (#9)
- 将 `actions/checkout` 升级到 v7 (#8)
- 在 `pyproject.toml` 中集中配置 ruff / pytest / coverage, 并按新规则整理 `core` 与入口代码格式, 移除未使用的导入

### 文档

- 更新 README 徽章, 并重新加入封面图

## [v0.2.1] - 2026-10-08

### 修复

- 将菜单项链接统一归一化为 `https://` 开头, 不再依赖用户手动补全协议 (#6)
- 支持在菜单条目为空时清空 QQ 机器人上已有的自定义菜单 (#6)

### 文档

- 修正一级菜单数量上限说明 (3 → 10), 并补充链接协议与同步行为提示 (#6)

## [v0.2.0] - 2026-10-08

### 新增

- 首次发布: 在 AstrBot WebUI 配置 QQ 官方机器人私聊自定义菜单, 插件启动时自动同步到 QQ (#2)
- 菜单配置改用 `template_list` 模板化结构, 支持 `发送消息` / `跳转链接` / `子菜单` 三类条目 (#4)
- 旧版 `dict` 菜单配置在首次加载时自动迁移为 `template_list` 并保存 (#4)
- 新增基于 `metadata.yaml` 版本变化的自动发布 workflow
- 新增 pullfrog workflow

### 修复

- 修复菜单配置 schema 类型错误导致插件加载失败的问题 (#3)

[v0.2.3]: https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/compare/v0.2.2...v0.2.3
[v0.2.2]: https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/compare/v0.2.1...v0.2.2
[v0.2.1]: https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/compare/v0.2.0...v0.2.1
[v0.2.0]: https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/releases/tag/v0.2.0
