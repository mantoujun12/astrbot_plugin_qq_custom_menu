<div align="center">

<img src="https://socialify.git.ci/mantoujun12/astrbot_plugin_qq_custom_menu/image?description=1&language=1&name=1&pattern=Circuit+Board&theme=Auto" alt="astrbot_plugin_qq_custom_menu" width="640" height="320" />

<!-- badge -->

[![CI Core](https://img.shields.io/github/actions/workflow/status/mantoujun12/astrbot_plugin_qq_custom_menu/ci.yml?style=flat-square&label=Core)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/actions/workflows/ci.yml)
[![CI Dashboard](https://img.shields.io/github/actions/workflow/status/mantoujun12/astrbot_plugin_qq_custom_menu/ci-dashboard.yml?style=flat-square&label=Dashboard)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/actions/workflows/ci-dashboard.yml)
[![Codecov](https://img.shields.io/codecov/c/github/mantoujun12/astrbot_plugin_qq_custom_menu?style=flat-square&logo=codecov&label=Coverage)](https://codecov.io/gh/mantoujun12/astrbot_plugin_qq_custom_menu)
[![GitHub Release](https://img.shields.io/github/v/release/mantoujun12/astrbot_plugin_qq_custom_menu?display_name=tag&style=flat-square)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/releases/latest)
[![GitHub last commit](https://img.shields.io/github/last-commit/mantoujun12/astrbot_plugin_qq_custom_menu?style=flat-square)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/commits/master)
[![AstrBot Plugin](https://img.shields.io/badge/AstrBot-Plugin-4984b9?style=flat-square&logo=github)](https://cloud.astrbot.app/plugin/mantoujun12/astrbot_plugin_qq_custom_menu)
[![GitHub Issues](https://img.shields.io/github/issues/mantoujun12/astrbot_plugin_qq_custom_menu?style=flat-square)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/mantoujun12/astrbot_plugin_qq_custom_menu?style=flat-square)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/pulls)
[![GitHub Repo stars](https://img.shields.io/github/stars/mantoujun12/astrbot_plugin_qq_custom_menu?style=flat-square)](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/stargazers)

<!-- badge -->

QQ 官方机器人私聊自定义菜单插件

在 **AstrBot WebUI** 中按机器人配置私聊自定义菜单。插件自带可视化 Dashboard，可查看同步状态、逐机器人编辑菜单，并把旧版全局配置保留在「兼容性」页。

</div>

## 核心特性

- **按机器人独立配置**：每台机器人拥有自己的 AppID、ClientSecret、平台类型和菜单内容，保存在 `data/plugin_data/astrbot_plugin_qq_custom_menu/menu_config.json`
- **私聊菜单**：写入 `GET/PUT /v2/menu`，支持发送消息、链接、子菜单和开关
- **兼容性配置**：旧版 `qq_platforms` + `menu` 继续可用，并与新版配置按 AppID 合并；新版接管同 AppID 后，旧配置不再影响该机器人
- **从兼容配置导入**：可在「机器人」页按 AppID 导入旧机器人，导入后仍可继续编辑
- **同步状态可视化**：Dashboard 状态页展示每个平台的 `已同步 / 待同步 / 尚未同步 / 同步已关闭` 状态
- **实时同步进度**：手动同步通过 SSE 推送逐平台、逐场景进度与日志，某个机器人失败不会中断其余机器人
- **凭证安全**：Dashboard 只展示 `ClientSecret` 掩码；保存时留空表示沿用已保存的密钥
- **链接自动归一化**：省略协议或误用 `http://` 的链接会统一补全为 QQ 要求的 `https://`
- **变更检测**：本地摘要记录上次成功同步的菜单，远端与配置一致时跳过 `PUT`，不信任过期摘要
- **国际化**：运行期日志与 Dashboard 均提供简体中文 / English

## 安装

插件面向 QQ 官方机器人（`qq_official` / `qq_official_webhook`），需要自行准备机器人的 `AppID` 与 `ClientSecret`。

1. **插件市场（推荐）**：在 AstrBot WebUI 的插件市场搜索 `astrbot_plugin_qq_custom_menu`，或直接打开[插件主页](https://cloud.astrbot.app/plugin/mantoujun12/astrbot_plugin_qq_custom_menu)安装。
2. **手动安装**：从 [Releases](https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu/releases/latest) 下载 zip，解压到 AstrBot 的 `data/plugins/` 下（解压后应得到一个包含 `main.py` 与 `metadata.yaml` 的插件目录），再重启 AstrBot 或在插件页重载插件；依赖会由插件管理器按 `requirements.txt` 安装。
3. 安装完成后打开本插件的可视化视图，按下面的「Dashboard」与「配置说明」维护菜单。

## 快速开始

1. 在 AstrBot 中安装并启用本插件。
2. 打开插件可视化视图，进入「机器人」页新增机器人并填写 `AppID` 与 `ClientSecret`。
3. 在机器人编辑器里维护「私聊」菜单，点击「保存并同步」。
4. 到「状态概览」页查看同步进度与每个平台的状态。
5. 旧版全局配置可在「兼容性」页继续维护，也可以在 AstrBot 插件配置页编辑。

> 插件启动时会自动同步一次。修改配置后可以重启 AstrBot / 重载插件，或在 Dashboard 里手动同步。

## Dashboard

Dashboard 构建产物提交在 `pages/dashboard/`，AstrBot 会把它作为插件视图加载。

| 页面 | 能力 |
| --- | --- |
| 状态概览 | 机器人统计、私聊菜单状态、手动同步与实时进度 |
| 机器人 | 逐机器人维护私聊自定义菜单，支持新增、编辑、删除、导入兼容配置 |
| 兼容性 | 维护旧版全局 `qq_platforms` 与私聊 `menu`，仅对未被新版接管的 AppID 生效 |
| 设置 | 日志语言、启动同步开关、插件版本与仓库入口 |

说明：

- 新版机器人凭证保存在 `menu_config.json`；兼容配置只使用兼容性页（或插件配置页）填写并由插件保存的凭证。
- 兼容配置的平台凭证为空时不会读取 AstrBot 平台配置，也不会因此触发同步。
- 本地 `pnpm dev` 没有 AstrBot bridge，页面会显示明确标注的 mock 数据，保存与同步不会伪装成功。

## 配置说明

### `language`

- 类型：`string`
- 可选：`zh-CN`、`en-US`、`ru-RU`、`ja-JP`
- 默认值：`zh-CN`
- 含义：插件运行期日志语言，不影响用户填写的菜单内容。

### `sync_menu`

- 类型：`bool`
- 默认值：`true`
- 含义：是否在启动时同步自定义菜单。
- 关闭后：插件只通过 `GET /v2/menu` 读取 QQ 当前菜单，不会覆盖线上内容；Dashboard 会显示「同步已关闭」。

### 兼容性 `qq_platforms`

- 类型：`template_list`
- 默认值：`[]`
- 含义：QQ 官方机器人平台凭证列表，每个条目包含：
  - `appid`：QQ 官方机器人 `AppID`
  - `secret`：QQ 官方机器人 `ClientSecret`
  - `platform`：平台类型，可选 `qq_official` / `qq_official_webhook`
- 留空时：不读取 AstrBot 平台配置，也不会同步未在插件中配置凭证的机器人。
- 多机器人场景下建议为每个机器人单独添加一条凭证。

### 兼容性 `menu`

- 类型：`template_list`
- 默认值：`[]`
- 含义：旧版全局 QQ 私聊自定义菜单内容，仅对未被 `menu_config.json` 按 AppID 接管的机器人生效。
- 模板 key：
  - `send_message`：发送消息菜单项，字段为 `name` / `message` / `parent`
  - `link`：跳转链接菜单项，字段为 `name` / `link` / `parent`
  - `switch`：开关菜单项，字段为 `name` / `switch_id` / `default`
  - `menu`：子菜单项，字段为 `name`
- 子菜单项通过 `parent` 字段引用母菜单名称，不内嵌。
- 一级菜单最多 10 个；每个子菜单最多 5 个子项。
- `link` 未填写协议时会自动归一化为 `https://` 开头。
- `menu` 为空且 `sync_menu` 开启时，会清空 QQ 机器人当前的远程自定义菜单。

### 新版机器人配置

Dashboard 的「机器人」页把配置写入插件数据目录，不写进仓库：

```json
{
  "version": 2,
  "robots": [
    {
      "id": "b7f6…",
      "name": "主机器人",
      "appid": "102xxxxxx",
      "secret": "••••••••",
      "platform": "qq_official",
      "scenes": {
        "c2c": {
          "enabled": true,
          "items": [
            { "type": "send_message", "name": "帮助", "message": "/help", "parent": "" }
          ]
        }
      }
    }
  ]
}
```

`version` 是乐观并发版本号，保存成功后会递增；页面提交旧版本时返回 HTTP 409，重新载入即可。

### 兼容性配置文件示例

```yaml
language: zh-CN
sync_menu: true
qq_platforms:
  - appid: "102xxxxxx"
    secret: "••••••••"
    platform: qq_official
menu:
  - __template_key: send_message
    name: 帮助
    message: /help
    parent: ""
  - __template_key: menu
    name: 更多
  - __template_key: link
    name: 文档
    link: https://docs.example.com
    parent: 更多
```

## 同步行为

1. 读取 `menu_config.json`，与兼容配置按 AppID 合并；新版配置优先接管同 AppID。
2. 对私聊场景创建 `QQClient`，先换取 `access_token`，再调用 `GET /v2/menu` 读取远端菜单。
3. `sync_menu` 开启时，将配置转换为 QQ 菜单结构；远端与配置一致则跳过 `PUT`，否则调用 `PUT /v2/menu` 整表覆盖。
4. 同步成功后把私聊菜单摘要写入 `menu_state.yaml`，供状态页判断是否已同步。
5. 单个机器人失败只影响对应机器人，Dashboard 会展示失败原因，其余机器人继续同步。
6. 私聊菜单为空且场景启用时，`PUT` 会清空该机器人的 QQ 自定义菜单。

## 开发与测试

插件通过 AstrBot 加载，功能测试仍需要在运行的 AstrBot 实例下进行；业务逻辑和 Dashboard 都可以跑离线测试。

### 后端（Python 3.10+）

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
pytest --cov --cov-branch --cov-report=xml --junitxml=junit.xml -o junit_family=legacy
ruff check . --fix
ruff format --check .
pre-commit run --all-files   # 可选，与 CI 同一套 hooks
```

- 用例都在 `tests/`，`tests/conftest.py` 会注入轻量 AstrBot stub，无需安装 AstrBot。
- `tests/test_main.py` 覆盖插件装配层；`tests/test_web_api.py` / `tests/test_sync_runner.py` 覆盖 Dashboard 后端；`tests/test_package_script.py` / `tests/test_bump_script.py` 覆盖发布脚本。
- 异步用例直接写 `async def`（`asyncio_mode = "auto"`）。

### Dashboard（Vue 3 + Vite 8 + Vuetify 4）

需要 Node `^22.12.0 || >=24` 与 pnpm 9+（CI 使用 Node 24 + pnpm 12，见 [package.json](web/dashboard/package.json) 的 `engines`）。源码在 `web/dashboard/`，构建产物提交在 `pages/dashboard/`：

```bash
cd web/dashboard
pnpm install
pnpm dev            # 本地 dev server，没有 bridge，走 mock 并显式标注
pnpm build          # vue-tsc 类型检查 + Vite 打包，直接写 pages/dashboard/
pnpm test           # Vitest 单次运行
pnpm test:coverage  # 覆盖率，阈值见 vitest.config.ts
pnpm test:report    # 额外产出 test-report.junit.xml
pnpm test:codecov   # 覆盖率 + JUnit，CI 用的入口
```

`pnpm build` 会先执行 `vue-tsc` 类型检查，并直接生成 `pages/dashboard/` 产物；不要手工编辑构建产物，改源码后重新构建即可。

### 打包与发布

```bash
python scripts/bump_version.py --check   # 校验三处版本号一致
python scripts/bump_version.py minor     # 同步 metadata.yaml / core/paths.py / web/dashboard/package.json
python scripts/package_plugin.py         # 生成 dist/<插件名>-<版本>.zip
```

`metadata.yaml` 是唯一版本源，三处版本号必须一致，否则自动发布工作流会拒绝发布。推送到 `master` 且 `metadata.yaml` 有改动时，[release.yml](.github/workflows/release.yml) 会校验版本、用 `scripts/package_plugin.py` 打包、打 tag 并创建 Release；发布是幂等的，失败可在 Actions 里手动重跑。

### 持续集成

- [ci.yml](.github/workflows/ci.yml)：pre-commit lint + Python 3.10 / 3.11 / 3.12 / 3.13 Pytest 矩阵
- [ci-dashboard.yml](.github/workflows/ci-dashboard.yml)：Node 24 + pnpm 12 上跑 Vitest、构建 Dashboard，并校验 `pages/dashboard` 无漂移
- [codecov-core.yml](.github/workflows/codecov-core.yml) / [codecov-dashboard.yml](.github/workflows/codecov-dashboard.yml)：把覆盖率与 JUnit 测试报告上传到 [Codecov](https://codecov.io/gh/mantoujun12/astrbot_plugin_qq_custom_menu)，前后端分别使用 flag `unittests` 与 `dashboard`

## 目录结构

```text
main.py                   插件入口（@register / initialize / terminate）
core/                     业务逻辑：config、menu、qq_api、state、sync_runner、web_api、paths、i18n
_conf_schema.json         WebUI 插件配置 schema
metadata.yaml             插件元数据（版本号唯一来源）
.astrbot-plugin/          WebUI 侧 i18n（metadata / config / views）
web/dashboard/            Dashboard 源码（Vue 3 + TypeScript + Vite + Vuetify + Vitest）
pages/dashboard/          Dashboard 构建产物（提交进仓库的生成文件）
tests/                    离线 pytest 套件
scripts/                  bump_version.py、package_plugin.py
.github/                  CI、Codecov、Release、Dependabot、Issue 模板
```

## 已知限制

### QQ 官方接口限制

- 一级菜单最多 10 个。
- 每个子菜单最多 5 个子项。
- 子菜单仅支持 `send_message` / `link`。
- `link` 必须为 `https://` 开头。
- 空菜单会清空远端自定义菜单。
- 本插件仅处理 C2C 单聊菜单；群聊功能由其他插件负责。

### 本项目限制

- 菜单同步只使用插件侧凭证（「机器人」或「兼容性」页填写），不会读取 AstrBot 平台配置。
- 菜单同步依赖 QQ 官方机器人开放平台的 Access Token 鉴权。
- 菜单展示效果受 QQ 官方机器人开放平台接口能力及当前适配器版本影响。
- Dashboard 的同步状态来自本地摘要，不会在每次打开页面时请求 QQ API；远端被外部修改后，状态可能仍显示「已同步」，下一次同步会以刚读取到的远端菜单为准。

## 下一步计划

- [x] i18n 国际化（简体中文 / English / Русский / 日本語）
- [x] 同步状态可视化 Dashboard
- [x] 同步结果的状态持久化与变更检测
- [x] 菜单编辑、机器人凭证维护与实时同步进度
- [x] 按机器人配置私聊自定义菜单
- [ ] 频道 / 频道私信场景支持
- [ ] 连接测试与更细的同步诊断

## 参考链接

- [AstrBot](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot 插件开发指南](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot Plugin Pages 文档](https://docs.astrbot.app/dev/star/guides/plugin-pages.html)
- [QQ 机器人开放平台 API v2 文档](https://bot.q.qq.com/wiki/develop/api-v2/)
- [QQ 机器人开放平台开发文档](https://bot.q.qq.com/wiki/)

## 许可证

本项目使用 AGPLv3 协议开源，详见 [LICENSE](LICENSE) 文件。
