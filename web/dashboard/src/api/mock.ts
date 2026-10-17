/**
 * 本地 `pnpm dev` 用的假数据。
 *
 * 覆盖已同步 / 待同步 / 未知几种状态，方便调样式；真实后端不会走到这里
 * （见 api/dashboard.ts 的 fetchStatus / fetchConfig）。
 */

import type { PluginConfigResponse, StatusResponse } from '../types/dashboard'

export const MOCK_STATUS: StatusResponse = {
  plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
  ready: true,
  sync_menu: true,
  state: { available: true },
  platforms: [
    {
      pf_id: '102*****89',
      appid: '102*****89',
      platform: 'qq_official',
      secret_set: true,
      source: 'plugin',
      state: 'synced',
    },
    {
      pf_id: '103*****88',
      appid: '103*****88',
      platform: 'qq_official_webhook',
      secret_set: true,
      source: 'plugin',
      state: 'pending',
    },
  ],
  menu: {
    top_level: 2,
    sub_items: 1,
    total: 3,
    top_level_max: 10,
    sub_items_max: 10,
    digest: 'mock-digest',
    items: [
      { type: 'send_message', name: '帮助', send_message: '/help' },
      {
        type: 'menu',
        name: '更多',
        sub_menu_items: [{ type: 'link', name: '文档', link: 'https://docs.example.com' }],
      },
    ],
  },
}

export const MOCK_CONFIG: PluginConfigResponse = {
  plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
  language: 'zh-CN',
  sync_menu: true,
  qq_platforms: [
    {
      appid: '1023456789',
      platform: 'qq_official',
      secret_masked: 'ab*****yz',
      secret_set: true,
    },
  ],
  runtime_platforms: [
    {
      pf_id: '102*****89',
      appid: '102*****89',
      platform: 'qq_official',
      secret_set: true,
      source: 'plugin',
    },
  ],
  using_fallback: false,
  menu: [
    { type: 'send_message', name: '帮助', message: '/help', parent: '' },
    { type: 'menu', name: '更多', parent: '' },
    { type: 'link', name: '文档', link: 'https://docs.example.com', parent: '更多' },
  ],
  limits: { top_level_max: 10, sub_items_max: 10 },
}
