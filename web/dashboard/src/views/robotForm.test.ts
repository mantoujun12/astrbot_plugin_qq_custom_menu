import { describe, expect, it } from 'vitest'
import {
  emptyRobotForm,
  robotItemCount,
  robotSceneCount,
  toRobotForm,
  validateRobotForm,
} from './robotForm'
import type { MenuLimits } from '../types/dashboard'
import type { RobotConfig } from '../types/robotConfig'

const t = (_key: string, fallback?: string): string => fallback ?? _key
const MENU_LIMITS: MenuLimits = { top_level_max: 10, sub_items_max: 5 }

function robot(): RobotConfig {
  return {
    id: 'robot-1',
    name: '主机器人',
    appid: 'app1',
    platform: 'qq_official',
    secret_masked: 'ab***yz',
    secret_set: true,
    scenes: {
      c2c: {
        enabled: true,
        items: [{ type: 'send_message', name: '帮助', message: '/help', parent: '' }],
      },
    },
  }
}

describe('robotForm helpers', () => {
  it('creates and converts private-chat robot forms', () => {
    expect(emptyRobotForm()).toMatchObject({
      id: '',
      platform: 'qq_official',
      scenes: {
        c2c: { enabled: true, items: [] },
      },
    })
    const form = toRobotForm(robot())
    expect(form.secret).toBe('')
    expect(form.scenes.c2c.items[0].name).toBe('帮助')
    expect(robotSceneCount(form)).toBe(1)
    expect(robotItemCount(form)).toBe(1)
  })

  it('validates and builds a normalized payload', () => {
    const form = toRobotForm(robot())
    form.name = ' 主机器人 '
    form.secret = ' new-secret '
    form.scenes.c2c.items.push({
      type: 'link',
      name: '官网',
      link: 'example.com',
      parent: '',
    })

    const checked = validateRobotForm(form, MENU_LIMITS, t)

    expect(checked.ok).toBe(true)
    expect(checked.payload).toMatchObject({
      name: '主机器人',
      secret: 'new-secret',
      scenes: {
        c2c: {
          enabled: true,
          items: [
            { type: 'send_message', name: '帮助', message: '/help', parent: '' },
            { type: 'link', name: '官网', link: 'https://example.com', parent: '' },
          ],
        },
      },
    })
  })

  it('rejects missing and overlong basic fields', () => {
    const missing = emptyRobotForm()
    expect(validateRobotForm(missing, MENU_LIMITS, t).ok).toBe(false)
    expect(
      validateRobotForm(
        { ...missing, name: 'x'.repeat(65), appid: 'app', secret: 'secret' },
        MENU_LIMITS,
        t,
      ).ok,
    ).toBe(false)
  })

  it('rejects invalid private-chat menu entries', () => {
    const form = toRobotForm(robot())
    form.secret = ''
    form.scenes.c2c.items = [
      { type: 'link', name: '无链接', link: '', parent: '' },
    ]
    const checked = validateRobotForm(form, MENU_LIMITS, t)
    expect(checked.ok).toBe(false)
    expect(checked.reason).toContain('缺少链接')
  })
})
