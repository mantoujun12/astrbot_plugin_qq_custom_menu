# Changelog

本文件记录本项目的所有重要变更。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/),
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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

[v0.2.2]: https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/compare/v0.2.1...v0.2.2
[v0.2.1]: https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/compare/v0.2.0...v0.2.1
[v0.2.0]: https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/releases/tag/v0.2.0
