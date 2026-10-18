import { readFileSync, readdirSync } from 'node:fs'
import { join, resolve } from 'node:path'
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

function lookup(value: unknown, path: string): unknown {
  return path.split('.').reduce<unknown>((node, key) => {
    if (!node || typeof node !== 'object') return undefined
    return (node as Record<string, unknown>)[key]
  }, value)
}

function sourceFiles(): string[] {
  const root = resolve(process.cwd(), 'src')
  return readdirSync(root, { recursive: true, withFileTypes: true })
    .filter(
      (entry) =>
        entry.isFile() &&
        /\.(ts|vue)$/.test(entry.name) &&
        !entry.name.endsWith('.test.ts'),
    )
    .map((entry) => join(entry.parentPath, entry.name))
}

describe('dashboard i18n resources', () => {
  it('defines the view metadata used by the host', () => {
    for (const locale of ['zh-CN', 'en-US']) {
      const data = loadLocale(locale)
      const view = (data.pages as Record<string, Record<string, unknown>>).dashboard
      expect(view.title).toBeTruthy()
      expect(view.description).toBeTruthy()
    }
  })

  it('keeps zh-CN and en-US key sets in sync', () => {
    const zh = loadLocale('zh-CN').pages as Record<string, unknown>
    const en = loadLocale('en-US').pages as Record<string, unknown>

    expect(keyPaths(en.dashboard)).toEqual(keyPaths(zh.dashboard))
  })

  it('uses the pages.dashboard root expected by plugin views', () => {
    for (const locale of ['zh-CN', 'en-US']) {
      const data = loadLocale(locale)
      expect(data.views).toBeUndefined()
      expect(
        (data.pages as Record<string, Record<string, unknown>>).dashboard.title,
      ).toBeTruthy()
    }
  })

  it('defines every statically referenced pages.dashboard key', () => {
    const keys = new Set<string>()
    const calls: Array<{ key: string; fallback: string; file: string }> = []
    for (const file of sourceFiles()) {
      const source = readFileSync(file, 'utf8')
      for (const match of source.matchAll(/\bt\(\s*'(pages\.dashboard\.[^']+)'/g)) {
        keys.add(match[1])
        const call = source.slice(match.index, match.index + 320)
        const fallback = call.match(/^t\(\s*'[^']+'\s*,\s*'([^']*)'/)?.[1]
        if (fallback !== undefined) {
          calls.push({ key: match[1], fallback, file })
        }
      }
    }
    expect(keys.size).toBeGreaterThan(50)
    for (const locale of ['zh-CN', 'en-US']) {
      const data = loadLocale(locale)
      const missing = [...keys].filter((key) => typeof lookup(data, key) !== 'string')
      expect(missing, locale).toEqual([])
    }

    const drifted = calls
      .filter((call) => lookup(loadLocale('zh-CN'), call.key) !== call.fallback)
      .map((call) => `${call.file}: ${call.key}`)
    expect(drifted).toEqual([])
  })
})
