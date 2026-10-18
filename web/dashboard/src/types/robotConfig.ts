/** 新版“机器人 → 私聊菜单”配置的数据契约。 */

import type { MenuEntry, MenuLimits, Scene } from './dashboard'

export interface C2cSceneConfig {
  enabled: boolean
  items: MenuEntry[]
}

export interface RobotConfig {
  id: string
  name: string
  appid: string
  platform: string
  secret_masked: string
  secret_set: boolean
  scenes: {
    c2c: C2cSceneConfig
  }
}

export interface RobotConfigResponse {
  plugin?: { name: string; version: string }
  version: number
  robots: RobotConfig[]
  available_scenes: Scene[]
  menu_limits: MenuLimits
}

export interface RobotConfigPayload {
  id: string
  name: string
  appid: string
  /** 留空表示沿用已有 ClientSecret。 */
  secret: string
  platform: string
  scenes: {
    c2c: C2cSceneConfig
  }
}

export interface RobotConfigSavePayload {
  version: number
  robots: RobotConfigPayload[]
}

export type RobotConfigForm = RobotConfigPayload
