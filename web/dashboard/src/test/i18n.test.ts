import { readFileSync, readdirSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { LOG_LEVELS } from '../types/logs'

const LOCALES = ['zh-CN', 'en-US', 'ru-RU', 'ja-JP']
const DEFAULT_LOCALE = 'zh-CN'

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

function leafStrings(value: unknown, prefix = ''): Array<[string, string]> {
  if (typeof value === 'string') {
    return [[prefix, value]]
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return []
  }
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
    leafStrings(child, prefix ? `${prefix}.${key}` : key),
  )
}

function placeholders(template: string): string[] {
  return [...new Set(template.match(/\{[^{}]+\}/g) ?? [])].sort()
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

const dictionaries = Object.fromEntries(
  LOCALES.map((locale) => [locale, loadLocale(locale)]),
) as Record<string, Record<string, unknown>>

describe('dashboard i18n resources', () => {
  it('ships every supported locale', () => {
    const files = readdirSync(
      resolve(process.cwd(), '../../.astrbot-plugin/i18n'),
    )
      .filter((name) => name.endsWith('.json'))
      .map((name) => name.slice(0, -'.json'.length))
      .sort()
    expect(files).toEqual([...LOCALES].sort())
  })

  it('defines the view metadata used by the host', () => {
    for (const locale of LOCALES) {
      const data = dictionaries[locale]
      const view = (data.pages as Record<string, Record<string, unknown>>).dashboard
      expect(view.title, locale).toBeTruthy()
      expect(view.description, locale).toBeTruthy()
    }
  })

  it('keeps every locale key set in sync with zh-CN', () => {
    const expected = keyPaths(dictionaries[DEFAULT_LOCALE])
    for (const locale of LOCALES) {
      expect(keyPaths(dictionaries[locale]), locale).toEqual(expected)
    }
  })

  it('keeps every placeholder in sync with zh-CN', () => {
    const expected = new Map(leafStrings(dictionaries[DEFAULT_LOCALE]))
    for (const locale of LOCALES) {
      const drifted = leafStrings(dictionaries[locale])
        .filter(([key, value]) => {
          const source = expected.get(key)
          return source !== undefined &&
            placeholders(source).join() !== placeholders(value).join()
        })
        .map(([key]) => key)
      expect(drifted, locale).toEqual([])
    }
  })

  it('uses the pages.dashboard root expected by plugin views', () => {
    for (const locale of LOCALES) {
      const data = dictionaries[locale]
      expect(data.views, locale).toBeUndefined()
      expect(
        (data.pages as Record<string, Record<string, unknown>>).dashboard.title,
        locale,
      ).toBeTruthy()
    }
  })

  it('exposes all four log languages to the settings page', () => {
    for (const locale of LOCALES) {
      const data = dictionaries[locale]
      const labels = lookup(data, 'config.language.labels')
      expect(labels, locale).toHaveLength(LOCALES.length)
      for (const language of LOCALES) {
        expect(
          lookup(data, `pages.dashboard.settings.languageName.${language}`),
          `${locale}: ${language}`,
        ).toBeTruthy()
      }
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
    for (const locale of LOCALES) {
      const data = dictionaries[locale]
      const missing = [...keys].filter((key) => typeof lookup(data, key) !== 'string')
      expect(missing, locale).toEqual([])
    }

    const drifted = calls
      .filter((call) => lookup(dictionaries[DEFAULT_LOCALE], call.key) !== call.fallback)
      .map((call) => `${call.file}: ${call.key}`)
    expect(drifted).toEqual([])
  })

  it('defines every log level label', () => {
    const keys = LOG_LEVELS.map((level) => `pages.dashboard.logs.levels.${level}`)
    for (const locale of LOCALES) {
      const missing = keys.filter(
        (key) => typeof lookup(dictionaries[locale], key) !== 'string',
      )
      expect(missing, locale).toEqual([])
    }
  })
})
