<div align="center">

<img src="https://socialify.git.ci/mantoujun12/astrbot_plugin_qq_custom_menu/image?description=1&language=1&name=1&pattern=Circuit+Board&theme=Auto" alt="astrbot_plugin_qq_custom_menu" width="640" height="320" />

<!-- badge -->

[![GitHub License](https://img.shields.io/github/license/mantoujun12/astrbot_plugin_qq_custom_menu)](LICENSE)
[![codecov](https://codecov.io/gh/mantoujun12/astrbot_plugin_qq_custom_menu/graph/badge.svg)](https://codecov.io/gh/mantoujun12/astrbot_plugin_qq_custom_menu)
[![CI](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/actions/workflows/ci.yml/badge.svg)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/mantoujun12/astrbot_plugin_qq_custom_menu?sort=date&display_name=tag)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/releases/latest)
[![GitHub last commit](https://img.shields.io/github/last-commit/mantoujun12/astrbot_plugin_qq_custom_menu)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/commits/master)
[![AstrBot](https://img.shields.io/badge/AstrBot-%234984b9?logo=Github)](https://github.com/AstrBotDevs/AstrBot)
[![AstrBot Plugin](https://img.shields.io/badge/AstrBot-Plugin-4984b9?logo=github)](https://cloud.astrbot.app/plugin/mantoujun12/astrbot_plugin_qq_custom_menu)
[![GitHub Issues](https://img.shields.io/github/issues/mantoujun12/astrbot_plugin_qq_custom_menu)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/mantoujun12/astrbot_plugin_qq_custom_menu)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/pulls)
[![GitHub Repo stars](https://img.shields.io/github/stars/mantoujun12/astrbot_plugin_qq_custom_menu)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/stargazers)

<!-- badge -->

QQ 官方机器人自定义菜单插件

在 **AstrBot WebUI** 中配置菜单内容，让 QQ 官方机器人在私聊场景展示自定义菜单。

</div>

## 核心特性

- 通过 **AstrBot WebUI** 配置 QQ 官方机器人要展示的菜单内容
- 菜单内容由用户自定义，便于根据实际使用场景组织常用入口
- 支持 QQ 官方机器人平台及 QQ 官方机器人 Webhook 平台
- 当前仅支持私聊场景

## 使用说明

1. 在 AstrBot 中安装并启用本插件。
2. 打开 **AstrBot WebUI → 插件配置**，填写 QQ 官方机器人 `AppID`、`ClientSecret`。
3. 在「QQ 私聊自定义菜单」中点击「添加条目」，按类型添加菜单项：
   - `发送消息`：填写菜单名称和点击后发送的消息，例如 `/help`
   - `跳转链接`：填写菜单名称和点击后打开的链接
   - `子菜单`：填写子菜单名称；再添加 `发送消息` 或 `跳转链接` 条目，并将「父菜单名称」填写为该子菜单名称，即可成为它的子项
4. 保存配置并按照 AstrBot 的提示重载插件或重启 AstrBot。
5. 插件启动时先通过 `GET /v2/menu` 读取当前菜单，再通过 QQ 菜单接口同步配置内容。

## 配置说明

### `sync_menu`

- 类型：`bool`
- 默认值：`true`
- 含义：启动时是否同步自定义菜单。
- 关闭后：仅读取 QQ 当前菜单，不会覆盖 QQ 机器人菜单。

### `qq_platforms`

- 类型：`template_list`
- 默认值：`[]`
- 含义：QQ 官方机器人平台凭证列表，每个条目包含：
  - `appid`：QQ 官方机器人 `AppID`
  - `secret`：QQ 官方机器人 `ClientSecret`
  - `platform`：平台类型，可选 `qq_official` / `qq_official_webhook`
- 留空时：回退读取 AstrBot 平台配置中的 QQ 官方平台。
- 建议：多机器人场景下为每个机器人单独添加一条凭证。

### `menu`

- 类型：`template_list`
- 默认值：`[]`
- 含义：QQ 私聊自定义菜单内容。
- 模板 key：
  - `send_message`：发送消息菜单项，字段为 `name` / `message` / `parent`
  - `link`：跳转链接菜单项，字段为 `name` / `link` / `parent`
  - `menu`：子菜单项，字段为 `name`；子菜单项通过 `parent` 字段引用母菜单名称
- 一级菜单最多 10 个。
- `link` 未填写协议时会自动归一化为 `https://` 开头。
- `menu` 为空且 `sync_menu` 开启时，会清空 QQ 机器人当前的远程自定义菜单。

## 已知限制

### QQ 官方接口限制

- 一级菜单最多 10 个。
- 子菜单仅支持 `send_message` / `link`。
- `link` 必须为 `https://` 开头。
- 空菜单会清空远端自定义菜单。

### 本项目限制

- 当前仅支持私聊场景。
- 使用前需要配置并启用 QQ 官方机器人适配器。
- 菜单同步依赖 QQ 官方机器人开放平台的 Access Token 鉴权。
- 菜单展示效果受 QQ 官方机器人开放平台接口能力及当前适配器版本影响。

## 下一步计划

- [ ] i18n 国际化
- [ ] 同步状态可视化 Dashboard
- [ ] 群聊 / 频道场景支持
- [ ] 同步结果的状态持久化与变更检测

## 相关链接

- [AstrBot](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot 插件开发指南](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot Plugin Pages 文档](https://docs.astrbot.app/dev/plugin-pages/index.html)
- [QQ 机器人开放平台 API v2 文档](https://bot.q.qq.com/wiki/develop/api-v2/)
- [QQ 机器人开放平台开发文档](https://bot.q.qq.com/wiki/)

## 许可证

本项目使用 AGPLv3 协议开源，详见 [LICENSE](LICENSE) 文件。