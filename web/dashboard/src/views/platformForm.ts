/**
 * 机器人凭证编辑页的纯函数：表单转换、校验与提交载荷。
 */

import type { ConfigPlatform } from '../types/dashboard'

export const PLATFORM_TYPES = ['qq_official', 'qq_official_webhook'] as const

export type PlatformType = (typeof PLATFORM_TYPES)[number]

export interface PlatformFormRow {
  appid: string
  secret: string
  platform: PlatformType
  /** 已保存密钥的掩码；新条目为空 */
  secret_masked: string
  /** 服务端是否已有密钥；true 时 secret 留空表示沿用 */
  secret_set: boolean
  isNew: boolean
}

export interface PlatformValidation {
  ok: boolean
  reason: string
}

export function toPlatformForm(platforms: ConfigPlatform[]): PlatformFormRow[] {
  return platforms.map((platform) => ({
    appid: platform.appid,
    secret: '',
    platform: PLATFORM_TYPES.includes(platform.platform as PlatformType)
      ? (platform.platform as PlatformType)
      : 'qq_official',
    secret_masked: platform.secret_masked,
    secret_set: platform.secret_set,
    isNew: false,
  }))
}

export function newPlatform(): PlatformFormRow {
  return {
    appid: '',
    secret: '',
    platform: 'qq_official',
    secret_masked: '',
    secret_set: false,
    isNew: true,
  }
}

/** 校验规则与 core/config.py 的 _normalize_platforms 对齐。 */
export function validatePlatforms(
  rows: PlatformFormRow[],
  t: (key: string, fallback?: string) => string,
): PlatformValidation {
  const seen = new Set<string>()
  for (let index = 0; index < rows.length; index += 1) {
    const row = rows[index]
    const appid = row.appid.trim()
    if (!appid) {
      return {
        ok: false,
        reason: t(
          'pages.dashboard.platforms.validation.appidEmpty',
          '第 {index} 个平台缺少 AppID',
        ).replace('{index}', String(index + 1)),
      }
    }
    if (seen.has(appid)) {
      return {
        ok: false,
        reason: t(
          'pages.dashboard.platforms.validation.duplicate',
          'AppID 重复：{appid}',
        ).replace('{appid}', appid),
      }
    }
    seen.add(appid)
    if (!PLATFORM_TYPES.includes(row.platform)) {
      return {
        ok: false,
        reason: t(
          'pages.dashboard.platforms.validation.typeInvalid',
          '平台 {appid} 的类型不合法',
        ).replace('{appid}', appid),
      }
    }
    if (!row.secret.trim() && !row.secret_set) {
      return {
        ok: false,
        reason: t(
          'pages.dashboard.platforms.validation.secretEmpty',
          '平台 {appid} 缺少 ClientSecret',
        ).replace('{appid}', appid),
      }
    }
  }
  return { ok: true, reason: '' }
}

export function buildPlatformPayload(rows: PlatformFormRow[]): {
  appid: string
  secret: string
  platform: string
}[] {
  return rows.map((row) => ({
    appid: row.appid.trim(),
    secret: row.secret.trim(),
    platform: row.platform,
  }))
}
