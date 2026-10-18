/**
 * 本地 `pnpm dev` 用的假数据。
 *
 * 覆盖已同步 / 待同步 / 未知几种状态，方便调样式；真实后端不会走到这里
 * （见 api/dashboard.ts 的 fetchStatus / fetchConfig）。
 */

import type { PluginConfigResponse, StatusResponse } from '../types/dashboard'
import type { RobotConfigResponse } from '../types/robotConfig'

export const MOCK_STATUS: StatusResponse = {
  plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
  ready: true,
  sync_menu: true,
  state: { available: true },
  platforms: [
    {
      pf_id: '102*****89',
      appid: '102*****89',
      name: '主机器人',
      platform: 'qq_official',
      secret_set: true,
      source: 'robot',
      state: 'synced',
      scenes: [
        {
          scene: 'c2c',
          enabled: true,
          state: 'synced',
          item_count: 2,
          digest: 'mock-c2c',
        },
      ],
    },
    {
      pf_id: '103*****88',
      appid: '103*****88',
      name: '兼容机器人',
      platform: 'qq_official_webhook',
      secret_set: true,
      source: 'compatibility',
      state: 'pending',
      scenes: [
        {
          scene: 'c2c',
          enabled: true,
          state: 'pending',
          item_count: 1,
          digest: 'mock-legacy',
        },
      ],
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
  robots: { new: 1, compatibility: 1 },
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
  menu: [
    { type: 'send_message', name: '帮助', message: '/help', parent: '' },
    { type: 'menu', name: '更多', parent: '' },
    { type: 'link', name: '文档', link: 'https://docs.example.com', parent: '更多' },
  ],
  limits: { top_level_max: 10, sub_items_max: 5 },
}

export const MOCK_ROBOTS: RobotConfigResponse = {
  plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
  version: 1,
  robots: [
    {
      id: 'mock-robot-1',
      name: '主机器人',
      appid: '1023456789',
      platform: 'qq_official',
      secret_masked: 'ab*****yz',
      secret_set: true,
      scenes: {
        c2c: {
          enabled: true,
          items: [
            { type: 'send_message', name: '帮助', message: '/help', parent: '' },
            { type: 'menu', name: '更多', parent: '' },
            {
              type: 'link',
              name: '文档',
              link: 'https://docs.example.com',
              parent: '更多',
            },
            {
              type: 'switch',
              name: '联网搜索',
              switch_id: 'search',
              default: false,
              parent: '',
            },
          ],
        },
      },
    },
  ],
  available_scenes: ['c2c'],
  menu_limits: { top_level_max: 10, sub_items_max: 5 },
}
