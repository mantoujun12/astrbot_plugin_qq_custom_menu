/**
 * 菜单编辑页的纯函数：克隆、增删改、校验与提交载荷。
 *
 * 抽出来是为了让所有规则都能脱离组件单测；视图只负责把结果映射到界面。
 */

import { MENU_TYPES } from '../types/dashboard'
import type { MenuEntry, MenuLimits, MenuType, QqMenuItem } from '../types/dashboard'

export interface MenuValidation {
  ok: boolean
  reason: string
}

/** 把后端返回的条目复制成可编辑副本，避免直接修改响应式数据源。 */
export function cloneEntries(entries: MenuEntry[]): MenuEntry[] {
  return entries.map((entry) => ({ ...entry }))
}

export function topLevelEntries(entries: MenuEntry[]): MenuEntry[] {
  return entries.filter((entry) => !entry.parent)
}

export function childEntries(entries: MenuEntry[], parent: string): MenuEntry[] {
  return entries.filter((entry) => entry.parent === parent)
}

export function newEntry(type: MenuType = 'send_message', parent = ''): MenuEntry {
  return {
    type,
    name: '',
    message: type === 'send_message' ? '' : undefined,
    link: type === 'link' ? '' : undefined,
    switch_id: type === 'switch' ? '' : undefined,
    default: type === 'switch' ? false : undefined,
    parent,
  }
}

/** 与后端 core/config.py 的 _normalize_link 保持一致。 */
export function normalizeLink(value: string): string {
  const text = value.trim()
  if (!text) {
    return ''
  }
  const lowered = text.toLowerCase()
  if (lowered.startsWith('https://')) {
    return `https://${text.slice('https://'.length)}`
  }
  if (lowered.startsWith('http://')) {
    return `https://${text.slice('http://'.length)}`
  }
  if (text.startsWith('//')) {
    return `https:${text}`
  }
  return `https://${text}`
}

/** 把一条编辑结果写回列表；重命名母菜单时同步更新子项的 parent。 */
export function replaceEntry(
  entries: MenuEntry[],
  target: MenuEntry,
  next: MenuEntry,
): MenuEntry[] {
  const oldName = target.name
  return entries.map((entry) => {
    if (entry === target) {
      return { ...next }
    }
    if (target.type === 'menu' && oldName && entry.parent === oldName) {
      return { ...entry, parent: next.name }
    }
    return entry
  })
}

/** 删除条目；删除母菜单时一并移除它的子项。 */
export function removeEntry(entries: MenuEntry[], target: MenuEntry): MenuEntry[] {
  return entries.filter(
    (entry) =>
      entry !== target &&
      !(target.type === 'menu' && target.name && entry.parent === target.name),
  )
}

/** 提交前校验，返回第一条错误；规则与 core/config.py 的 _normalize_menu_entries 对齐。 */
export function validateMenu(
  entries: MenuEntry[],
  limits: MenuLimits,
  t: (key: string, fallback?: string) => string,
): MenuValidation {
  const topLevel = topLevelEntries(entries)
  const menuNames = new Set(
    entries.filter((entry) => entry.type === 'menu' && !entry.parent).map((entry) => entry.name),
  )
  const childNames = new Map<string, Set<string>>()
  const switchIds = new Set<string>()

  if (topLevel.length > limits.top_level_max) {
    return {
      ok: false,
      reason: t(
        'pages.dashboard.menu.validation.topLimit',
        '一级菜单最多 {max} 个',
      ).replace('{max}', String(limits.top_level_max)),
    }
  }

  const names = topLevel.map((entry) => entry.name.trim())
  if (new Set(names).size !== names.length) {
    return {
      ok: false,
      reason: t('pages.dashboard.menu.validation.duplicate', '一级菜单名称不能重复'),
    }
  }

  for (const entry of entries) {
    const name = entry.name.trim()
    if (!name) {
      return {
        ok: false,
        reason: t('pages.dashboard.menu.validation.nameEmpty', '菜单名称不能为空'),
      }
    }
    if (entry.type === 'menu' && entry.parent) {
      return {
        ok: false,
        reason: t(
          'pages.dashboard.menu.validation.menuParent',
          '子菜单不能设置父菜单',
        ),
      }
    }
    if (entry.type === 'switch' && entry.parent) {
      return {
        ok: false,
        reason: t(
          'pages.dashboard.menu.validation.switchParent',
          '开关不能作为子菜单项',
        ),
      }
    }
    if (entry.parent && !menuNames.has(entry.parent)) {
      return {
        ok: false,
        reason: t(
          'pages.dashboard.menu.validation.parentMissing',
          '父菜单「{parent}」不存在',
        ).replace('{parent}', entry.parent),
      }
    }
    if (entry.parent) {
      const siblingNames = childNames.get(entry.parent) ?? new Set<string>()
      if (siblingNames.has(name)) {
        return {
          ok: false,
          reason: t(
            'pages.dashboard.menu.validation.childDuplicate',
            '子菜单「{parent}」下的子项名称「{name}」不能重复',
          )
            .replace('{parent}', entry.parent)
            .replace('{name}', name),
        }
      }
      siblingNames.add(name)
      childNames.set(entry.parent, siblingNames)
    }
    if (entry.type === 'send_message' && !(entry.message ?? '').trim()) {
      return {
        ok: false,
        reason: t(
          'pages.dashboard.menu.validation.messageEmpty',
          '菜单「{name}」缺少消息内容',
        ).replace('{name}', name),
      }
    }
    if (entry.type === 'link' && !(entry.link ?? '').trim()) {
      return {
        ok: false,
        reason: t(
          'pages.dashboard.menu.validation.linkEmpty',
          '菜单「{name}」缺少链接',
        ).replace('{name}', name),
      }
    }
    if (entry.type === 'switch') {
      const switchId = (entry.switch_id ?? '').trim()
      if (!switchId) {
        return {
          ok: false,
          reason: t(
            'pages.dashboard.menu.validation.switchIdEmpty',
            '菜单「{name}」缺少开关 ID',
          ).replace('{name}', name),
        }
      }
      if (switchIds.has(switchId)) {
        return {
          ok: false,
          reason: t(
            'pages.dashboard.menu.validation.switchIdDuplicate',
            '开关 ID 不能重复：{switchId}',
          ).replace('{switchId}', switchId),
        }
      }
      switchIds.add(switchId)
    }
  }

  for (const menuName of menuNames) {
    const count = childEntries(entries, menuName).length
    if (count > limits.sub_items_max) {
      return {
        ok: false,
        reason: t(
          'pages.dashboard.menu.validation.subLimit',
          '子菜单「{name}」最多 {max} 个子项',
        )
          .replace('{name}', menuName)
          .replace('{max}', String(limits.sub_items_max)),
      }
    }
  }

  return { ok: true, reason: '' }
}

/** 把 /status 返回的 QQ 菜单树还原成编辑用的扁平条目，供状态页预览。 */
export function qqItemsToEntries(items: QqMenuItem[], parent = ''): MenuEntry[] {
  const entries: MenuEntry[] = []
  for (const item of items) {
    const type = (MENU_TYPES as readonly string[]).includes(item.type)
      ? (item.type as MenuType)
      : 'send_message'
    const entry: MenuEntry = { type, name: item.name, parent }
    if (type === 'send_message') {
      entry.message = item.send_message ?? ''
    } else if (type === 'link') {
      entry.link = item.link ?? ''
    } else if (type === 'switch') {
      entry.switch_id = item.switch?.switch_id ?? ''
      entry.default = item.switch?.default ?? false
    }
    entries.push(entry)
    if (type === 'menu') {
      entries.push(...qqItemsToEntries(item.sub_menu_items ?? [], item.name))
    }
  }
  return entries
}

/** 生成提交给后端的菜单载荷，统一 trim 并补全链接协议。 */
export function buildMenuPayload(entries: MenuEntry[]): MenuEntry[] {
  return entries.map((entry) => {
    const payload: MenuEntry = {
      type: entry.type,
      name: entry.name.trim(),
      parent: entry.parent.trim(),
    }
    if (entry.type === 'send_message') {
      payload.message = (entry.message ?? '').trim()
    } else if (entry.type === 'link') {
      payload.link = normalizeLink(entry.link ?? '')
    } else if (entry.type === 'switch') {
      payload.switch_id = (entry.switch_id ?? '').trim()
      payload.default = entry.default === true
    }
    return payload
  })
}
