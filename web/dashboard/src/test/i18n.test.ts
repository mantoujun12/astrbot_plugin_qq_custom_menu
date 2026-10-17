import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function loadLocale(locale: string): Record<string, unknown> {
  // Vitest 的 cwd 是 web/dashboard，仓库根在两级之上。
  const path = resolve(
    process.cwd(),
    '../../.astrbot-plugin/i18n',
    `${locale}.json`,
  )
  return JSON.parse(readFileSync(path, 'utf-8')) as Record<string, unknown>
}

function keyPaths(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return [prefix]
  }
  return Object.entries(value as Record<string, unknown>)
    .flatMap(([key, child]) => keyPaths(child, prefix ? `${prefix}.${key}` : key))
    .sort()
}

describe('dashboard i18n resources', () => {
  it('defines the view metadata used by the host', () => {
    for (const locale of ['zh-CN', 'en-US']) {
      const data = loadLocale(locale)
      const view = (data.views as Record<string, Record<string, unknown>>).dashboard
      expect(view.title).toBeTruthy()
      expect(view.description).toBeTruthy()
    }
  })

  it('keeps zh-CN and en-US key sets in sync', () => {
    const zh = loadLocale('zh-CN').views as Record<string, unknown>
    const en = loadLocale('en-US').views as Record<string, unknown>

    expect(keyPaths(en.dashboard)).toEqual(keyPaths(zh.dashboard))
  })
})
