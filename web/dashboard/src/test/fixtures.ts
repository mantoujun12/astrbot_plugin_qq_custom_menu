/**
 * 组件测试共享的响应假件。
 *
 * 视图与 API 测试都会构造 /config、/status、/robots 的返回值；集中在这里可以
 * 保证字段与后端契约一致，避免每个文件各写一份逐渐漂移。
 */

import type {
  MenuEntry,
  MenuLimits,
  PlatformStatus,
  PluginConfigResponse,
  StatusResponse,
} from '../types/dashboard'
import type { LogEvent } from '../types/logs'
import type { RobotConfig, RobotConfigResponse } from '../types/robotConfig'

export const MENU_LIMITS: MenuLimits = { top_level_max: 10, sub_items_max: 5 }

export const MENU_ENTRIES: MenuEntry[] = [
  { type: 'send_message', name: '帮助', message: '/help', parent: '' },
  { type: 'menu', name: '更多', parent: '' },
  { type: 'link', name: '文档', link: 'https://docs.app', parent: '更多' },
]

export function pluginConfigFixture(
  overrides: Partial<PluginConfigResponse> = {},
): PluginConfigResponse {
  return {
    plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
    language: 'zh-CN',
    sync_menu: true,
    primary_color: '#3c96ca',
    secondary_color: '#2f86bd',
    qq_platforms: [
      {
        appid: '1023456789',
        platform: 'qq_official',
        secret_masked: 'ab***yz',
        secret_set: true,
      },
    ],
    runtime_platforms: [],
    menu: MENU_ENTRIES.map((entry) => ({ ...entry })),
    limits: MENU_LIMITS,
    ...overrides,
  }
}

export function platformFixture(overrides: Partial<PlatformStatus> = {}): PlatformStatus {
  return {
    pf_id: '102*****89',
    appid: '102*****89',
    name: '主机器人',
    platform: 'qq_official',
    secret_set: true,
    source: 'compatibility',
    state: 'synced',
    scenes: [
      {
        scene: 'c2c',
        enabled: true,
        state: 'synced',
        item_count: 2,
        digest: 'c2c',
      },
    ],
    ...overrides,
  }
}

export function statusFixture(overrides: Partial<StatusResponse> = {}): StatusResponse {
  return {
    plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
    ready: true,
    sync_menu: true,
    state: { available: true },
    platforms: [platformFixture()],
    menu: {
      top_level: 2,
      sub_items: 1,
      total: 3,
      top_level_max: 10,
      sub_items_max: 10,
      digest: 'digest',
      items: [
        { type: 'send_message', name: '帮助', send_message: '/help' },
        {
          type: 'menu',
          name: '更多',
          sub_menu_items: [{ type: 'link', name: '文档', link: 'https://docs.app' }],
        },
      ],
    },
    ...overrides,
  }
}

export function robotFixture(overrides: Partial<RobotConfig> = {}): RobotConfig {
  return {
    id: 'robot-1',
    name: '主机器人',
    appid: '1023456789',
    platform: 'qq_official',
    secret_masked: 'ab***yz',
    secret_set: true,
    scenes: {
      c2c: {
        enabled: true,
        items: MENU_ENTRIES.map((entry) => ({ ...entry })),
      },
    },
    ...overrides,
  }
}

export function robotResponseFixture(
  overrides: Partial<RobotConfigResponse> = {},
): RobotConfigResponse {
  return {
    version: 1,
    robots: [robotFixture()],
    available_scenes: ['c2c'],
    menu_limits: MENU_LIMITS,
    ...overrides,
  }
}

export function logEvent(seq = 1, overrides: Partial<LogEvent> = {}): LogEvent {
  return {
    type: 'log',
    seq,
    timestamp: `2026-10-23T02:18:0${seq}.000Z`,
    level: 'info',
    message: `message-${seq}`,
    ...overrides,
  }
}
