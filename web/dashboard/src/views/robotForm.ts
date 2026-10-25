/** 机器人私聊菜单配置页的纯函数：表单转换、校验和统计。 */

import { buildMenuPayload, cloneEntries, validateMenu } from './menuForm'
import type { MenuLimits } from '../types/dashboard'
import type {
  RobotConfig,
  RobotConfigForm,
  RobotConfigPayload,
} from '../types/robotConfig'

export interface RobotValidation {
  ok: boolean
  reason: string
  payload?: RobotConfigPayload
}

export function emptyRobotForm(): RobotConfigForm {
  return {
    id: '',
    name: '',
    appid: '',
    secret: '',
    platform: 'qq_official',
    scenes: {
      c2c: { enabled: true, items: [] },
    },
  }
}

export function toRobotForm(robot: RobotConfig): RobotConfigForm {
  return {
    id: robot.id,
    name: robot.name,
    appid: robot.appid,
    secret: '',
    platform: robot.platform,
    scenes: {
      c2c: {
        enabled: robot.scenes.c2c.enabled,
        items: cloneEntries(robot.scenes.c2c.items),
      },
    },
  }
}

export function robotItemCount(form: RobotConfigForm): number {
  return form.scenes.c2c.items.length
}

export function robotSceneCount(form: RobotConfigForm): number {
  return Number(form.scenes.c2c.enabled)
}

export function validateRobotForm(
  form: RobotConfigForm,
  menuLimits: MenuLimits,
  t: (key: string, fallback?: string) => string,
): RobotValidation {
  const name = form.name.trim()
  const appid = form.appid.trim()
  if (!name) {
    return {
      ok: false,
      reason: t(
        'pages.dashboard.robots.validation.nameEmpty',
        '机器人名称不能为空',
      ),
    }
  }
  if ([...name].length > 64) {
    return {
      ok: false,
      reason: t(
        'pages.dashboard.robots.validation.nameTooLong',
        '机器人名称最多 {max} 个字符',
      ).replace('{max}', '64'),
    }
  }
  if (!appid) {
    return {
      ok: false,
      reason: t(
        'pages.dashboard.robots.validation.appidEmpty',
        'AppID 不能为空',
      ),
    }
  }
  if (!form.secret.trim() && !form.id) {
    return {
      ok: false,
      reason: t(
        'pages.dashboard.robots.validation.secretEmpty',
        '新增机器人必须填写 ClientSecret',
      ),
    }
  }
  if (form.scenes.c2c.enabled) {
    const checked = validateMenu(form.scenes.c2c.items, menuLimits, t)
    if (!checked.ok) return { ok: false, reason: checked.reason }
  }

  return {
    ok: true,
    reason: '',
    payload: {
      id: form.id,
      name,
      appid,
      secret: form.secret.trim(),
      platform: form.platform,
      scenes: {
        c2c: {
          enabled: form.scenes.c2c.enabled,
          items: buildMenuPayload(form.scenes.c2c.items),
        },
      },
    },
  }
}

