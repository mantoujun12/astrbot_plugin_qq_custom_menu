/**
 * 状态接口（/status）、配置接口（/config）与同步进度流（/sync/events）的数据契约，
 * 与 core/web_api.py、core/menu.py、core/sync_runner.py 的结构一一对应。
 */

export const MENU_TYPES = ['send_message', 'link', 'menu'] as const

export type MenuType = (typeof MENU_TYPES)[number]

/** Dashboard 编辑用的扁平菜单条目；parent 为空表示一级菜单。 */
export interface MenuEntry {
  type: MenuType
  name: string
  message?: string
  link?: string
  parent: string
}

/** synced=本地摘要与当前配置一致，pending=配置已变，unknown=尚未同步，disabled=未开启同步。 */
export type SyncState = 'synced' | 'pending' | 'unknown' | 'disabled'

export interface PlatformStatus {
  /** 脱敏后的平台标识 */
  pf_id: string
  /** 脱敏后的 appid */
  appid: string
  platform: string
  secret_set: boolean
  source: 'plugin' | 'astrbot'
  state: SyncState
}

export interface QqMenuItem {
  type: string
  name: string
  send_message?: string
  link?: string
  sub_menu_items?: QqMenuItem[]
}

export interface MenuStats {
  top_level: number
  sub_items: number
  total: number
  top_level_max: number
  sub_items_max: number
  digest: string
  items: QqMenuItem[]
}

export interface StatusResponse {
  plugin: { name: string; version: string }
  ready: boolean
  sync_menu: boolean
  platforms: PlatformStatus[]
  menu: MenuStats
  state: { available: boolean }
}

/** 配置接口里的平台条目：secret 只回掩码。 */
export interface ConfigPlatform {
  appid: string
  platform: string
  secret_masked: string
  secret_set: boolean
}

export interface RuntimePlatform {
  pf_id: string
  appid: string
  platform: string
  secret_set: boolean
  source: 'plugin' | 'astrbot'
}

export interface MenuLimits {
  top_level_max: number
  sub_items_max: number
}

export interface PluginConfigResponse {
  plugin: { name: string; version: string }
  language: string
  sync_menu: boolean
  qq_platforms: ConfigPlatform[]
  runtime_platforms: RuntimePlatform[]
  using_fallback: boolean
  menu: MenuEntry[]
  limits: MenuLimits
}

/** 提交给 /config 的平台条目：secret 留空表示沿用同 appid 的已保存密钥。 */
export interface ConfigPlatformPayload {
  appid: string
  secret: string
  platform: string
}

/** 后端按字段合并，页面只提交自己负责的字段。 */
export interface PluginConfigPayload {
  language?: string
  sync_menu?: boolean
  qq_platforms?: ConfigPlatformPayload[]
  menu?: MenuEntry[]
}

export interface SyncMessageEvent {
  type: 'message'
  seq: number
  text: string
}

export interface SyncStartEvent {
  type: 'start'
  seq: number
  mode: 'sync' | 'read'
  platforms: number
  items: number
}

export interface SyncPlatformEvent {
  type: 'platform'
  seq: number
  pf_id: string
  index: number
  total: number
  status: 'ok' | 'error'
  action?: 'updated' | 'unchanged' | 'read' | 'failed'
  saved?: number
  error?: string | null
}

export interface SyncFinishEvent {
  type: 'finish'
  seq: number
  ok: boolean
  reason?: string
  platforms: number
  succeeded: number
  failed: number
  error?: string | null
}

export type SyncEvent =
  | SyncMessageEvent
  | SyncStartEvent
  | SyncPlatformEvent
  | SyncFinishEvent

export interface SyncPlatformState {
  pf_id: string
  index: number
  status: 'ok' | 'error'
  saved: number
  error: string
}

export interface SyncRunState {
  status: 'idle' | 'running' | 'done' | 'failed'
  /** 本轮要同步的平台数，来自 start 事件 */
  platforms: number
  completed: number
  succeeded: number
  failed: number
  messages: string[]
  platformStates: SyncPlatformState[]
  /** 已收到的最大 seq，重连时用它续订 */
  lastSeq: number
  error: string
}
