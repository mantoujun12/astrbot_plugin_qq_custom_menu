<div align="center">

# astrbot_plugin_qq_custom_menu

[![GitHub License](https://img.shields.io/github/license/mantoujun12/astrbot_plugin_qq_custom_menu?style=for-the-badge)](LICENSE)
![GitHub Release](https://img.shields.io/github/v/release/mantoujun12/astrbot_plugin_qq_custom_menu?sort=date&display_name=tag&style=for-the-badge)
![GitHub Repo stars](https://img.shields.io/github/stars/mantoujun12/astrbot_plugin_qq_custom_menu?style=for-the-badge)
[![AstrBot](https://img.shields.io/badge/AstrBot-%234984b9?style=for-the-badge&logo=Github)](https://github.com/AstrBotDevs/AstrBot)

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
2. 打开 **AstrBot WebUI → 插件配置**，填写自定义菜单内容。
3. 保存配置并按照 AstrBot 的提示重载插件或重启 AstrBot。
4. 在 QQ 私聊机器人，检查自定义菜单是否正常展示。

> 菜单展示效果受 QQ 官方机器人开放平台接口能力及当前适配器版本影响。

## 已知限制

- 当前仅支持私聊场景，不支持群聊、子频道或频道私信。
- 使用前需要配置并启用 QQ 官方机器人相关适配器。
- QQ 官方机器人菜单接口的具体限制以官方文档为准。

## 相关链接

- [AstrBot](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot 插件开发指南](https://docs.astrbot.app/dev/star/plugin-new.html)
- [QQ 机器人开放平台开发文档](https://bot.q.qq.com/wiki/)

## 许可证

本项目使用 AGPLv3 协议开源，详见 [LICENSE](LICENSE) 文件。
