import { describe, expect, it } from 'vitest'
import {
  buildMenuPayload,
  childEntries,
  cloneEntries,
  newEntry,
  normalizeLink,
  qqItemsToEntries,
  removeEntry,
  replaceEntry,
  topLevelEntries,
  validateMenu,
} from './menuForm'
import type { MenuEntry, MenuLimits } from '../types/dashboard'

const LIMITS: MenuLimits = { top_level_max: 10, sub_items_max: 5 }
const t = (_key: string, fallback?: string): string => fallback ?? _key

function entry(overrides: Partial<MenuEntry> = {}): MenuEntry {
  return { type: 'send_message', name: '帮助', message: '/help', parent: '', ...overrides }
}

describe('menuForm helpers', () => {
  it('clones entries and splits top-level from children', () => {
    const source = [entry(), entry({ type: 'menu', name: '更多', message: undefined })]
    const clone = cloneEntries(source)

    expect(clone).toEqual(source)
    expect(clone).not.toBe(source)
    expect(clone[0]).not.toBe(source[0])

    const withChild = [...source, entry({ name: '关于', parent: '更多' })]
    expect(topLevelEntries(withChild).map((item) => item.name)).toEqual(['帮助', '更多'])
    expect(childEntries(withChild, '更多').map((item) => item.name)).toEqual(['关于'])
  })

  it('creates entries with the fields required by their type', () => {
    expect(newEntry()).toEqual({
      type: 'send_message',
      name: '',
      message: '',
      link: undefined,
      switch_id: undefined,
      default: undefined,
      parent: '',
    })
    expect(newEntry('link', '更多')).toEqual({
      type: 'link',
      name: '',
      message: undefined,
      link: '',
      switch_id: undefined,
      default: undefined,
      parent: '更多',
    })
    expect(newEntry('menu')).toEqual({
      type: 'menu',
      name: '',
      message: undefined,
      link: undefined,
      switch_id: undefined,
      default: undefined,
      parent: '',
    })
    expect(newEntry('switch')).toEqual({
      type: 'switch',
      name: '',
      message: undefined,
      link: undefined,
      switch_id: '',
      default: false,
      parent: '',
    })
  })

  it('normalizes links like the backend', () => {
    expect(normalizeLink('  https://a.com  ')).toBe('https://a.com')
    expect(normalizeLink('http://a.com')).toBe('https://a.com')
    expect(normalizeLink('//a.com')).toBe('https://a.com')
    expect(normalizeLink('a.com')).toBe('https://a.com')
    expect(normalizeLink('   ')).toBe('')
  })

  it('replaces an entry and renames children with their parent', () => {
    const menu = entry({ type: 'menu', name: '更多', message: undefined })
    const child = entry({ name: '关于', parent: '更多' })
    const entries = [menu, child]

    const renamed = replaceEntry(entries, menu, { ...menu, name: '其它' })
    expect(renamed[0].name).toBe('其它')
    expect(renamed[1].parent).toBe('其它')

    const editedChild = replaceEntry(entries, child, { ...child, name: '介绍' })
    expect(editedChild[1].name).toBe('介绍')
  })

  it('removes a menu together with its children', () => {
    const menu = entry({ type: 'menu', name: '更多', message: undefined })
    const child = entry({ name: '关于', parent: '更多' })
    const other = entry({ name: '帮助' })

    expect(removeEntry([menu, child, other], menu)).toEqual([other])
    expect(removeEntry([menu, child, other], child)).toEqual([menu, other])
  })

  it('accepts a valid tree', () => {
    const entries = [
      entry(),
      entry({ type: 'menu', name: '更多', message: undefined }),
      entry({ name: '关于', message: '/about', parent: '更多' }),
      entry({ type: 'link', name: '文档', message: undefined, link: 'docs.app', parent: '更多' }),
      entry({ type: 'switch', name: '联网', switch_id: 'search', default: false }),
    ]
    expect(validateMenu(entries, LIMITS, t)).toEqual({ ok: true, reason: '' })
  })

  it('rejects invalid trees', () => {
    const cases: MenuEntry[][] = [
      Array.from({ length: 11 }, (_, index) =>
        entry({ name: `菜单${index}`, message: '/x' }),
      ),
      [entry({ name: '重复' }), entry({ name: '重复' })],
      [entry({ name: '  ' })],
      [entry({ type: 'menu', name: '子菜单', message: undefined, parent: '父' })],
      [entry({ name: '孤儿', message: '/x', parent: '不存在' })],
      [entry({ name: '无消息', message: '  ' })],
      [entry({ type: 'link', name: '无链接', message: undefined, link: '  ' })],
      [entry({ type: 'switch', name: '缺开关 ID', switch_id: '  ', default: false })],
      [
        entry({ type: 'switch', name: '开关一', switch_id: 'same', default: false }),
        entry({ type: 'switch', name: '开关二', switch_id: 'same', default: true }),
      ],
      [
        entry({ type: 'menu', name: '更多', message: undefined }),
        ...Array.from({ length: 11 }, (_, index) =>
          entry({ name: `子项${index}`, message: '/x', parent: '更多' }),
        ),
      ],
    ]

    for (const entries of cases) {
      const result = validateMenu(entries, LIMITS, t)
      expect(result.ok, JSON.stringify(entries)).toBe(false)
      expect(result.reason).not.toBe('')
    }
  })

  it('rejects duplicate child names within the same parent', () => {
    const entries = [
      entry({ type: 'menu', name: '更多', message: undefined }),
      entry({ name: '帮助', message: '/help', parent: '更多' }),
      entry({ name: '帮助', message: '/help-2', parent: '更多' }),
    ]

    expect(validateMenu(entries, LIMITS, t)).toEqual({
      ok: false,
      reason: '子菜单「更多」下的子项名称「帮助」不能重复',
    })
  })

  it('allows the same child name under different parents', () => {
    const entries = [
      entry({ type: 'menu', name: '更多', message: undefined }),
      entry({ type: 'menu', name: '其它', message: undefined }),
      entry({ name: '帮助', message: '/help', parent: '更多' }),
      entry({ name: '帮助', message: '/other-help', parent: '其它' }),
    ]

    expect(validateMenu(entries, LIMITS, t)).toEqual({ ok: true, reason: '' })
  })

  it('reports invalid entries before quota errors', () => {
    const cases: MenuEntry[][] = [
      [
        ...Array.from({ length: LIMITS.top_level_max }, (_, index) =>
          entry({ name: `菜单${index}`, message: '/x' }),
        ),
        entry({ name: '缺少消息', message: '' }),
      ],
      [
        entry({ type: 'menu', name: '更多', message: undefined }),
        ...Array.from({ length: LIMITS.sub_items_max }, (_, index) =>
          entry({ name: `子项${index}`, message: '/x', parent: '更多' }),
        ),
        entry({ name: '缺少消息', message: '', parent: '更多' }),
      ],
      [
        ...Array.from({ length: LIMITS.top_level_max }, (_, index) =>
          entry({ name: `菜单${index}`, message: '/x' }),
        ),
        entry({ type: 'link', name: '缺少链接', message: undefined, link: '' }),
      ],
      [
        entry({ type: 'menu', name: '更多', message: undefined }),
        ...Array.from({ length: LIMITS.sub_items_max }, (_, index) =>
          entry({ name: `子项${index}`, message: '/x', parent: '更多' }),
        ),
        entry({
          type: 'link',
          name: '缺少链接',
          message: undefined,
          link: '',
          parent: '更多',
        }),
      ],
    ]

    for (const entries of cases) {
      const result = validateMenu(entries, LIMITS, t)
      expect(result.ok).toBe(false)
      expect(result.reason).toContain('缺少')
      expect(result.reason).not.toContain('最多')
    }
  })

  it('builds a trimmed payload with normalized links', () => {
    const entries = [
      entry({ name: ' 帮助 ', message: ' /help ' }),
      entry({ type: 'menu', name: '更多', message: undefined }),
      entry({ type: 'link', name: '文档', message: undefined, link: ' docs.app ' }),
      entry({ type: 'switch', name: ' 联网 ', switch_id: ' search ', default: true }),
    ]
    expect(buildMenuPayload(entries)).toEqual([
      { type: 'send_message', name: '帮助', parent: '', message: '/help' },
      { type: 'menu', name: '更多', parent: '' },
      { type: 'link', name: '文档', parent: '', link: 'https://docs.app' },
      {
        type: 'switch',
        name: '联网',
        parent: '',
        switch_id: 'search',
        default: true,
      },
    ])
  })

  it('converts the QQ menu tree back into editor entries', () => {
    const items = [
      { type: 'send_message', name: '帮助', send_message: '/help' },
      {
        type: 'menu',
        name: '更多',
        sub_menu_items: [
          { type: 'link', name: '文档', link: 'https://docs.app' },
          { type: 'unknown', name: '未知' },
        ],
      },
      {
        type: 'switch',
        name: '联网',
        switch: { switch_id: 'search', default: true },
      },
    ]

    expect(qqItemsToEntries(items)).toEqual([
      { type: 'send_message', name: '帮助', parent: '', message: '/help' },
      { type: 'menu', name: '更多', parent: '' },
      { type: 'link', name: '文档', parent: '更多', link: 'https://docs.app' },
      { type: 'send_message', name: '未知', parent: '更多', message: '' },
      {
        type: 'switch',
        name: '联网',
        parent: '',
        switch_id: 'search',
        default: true,
      },
    ])
  })
})
