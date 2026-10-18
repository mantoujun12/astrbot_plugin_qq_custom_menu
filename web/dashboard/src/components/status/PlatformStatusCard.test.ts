import { describe, expect, it } from 'vitest'
import PlatformStatusCard from './PlatformStatusCard.vue'
import { mountView } from '../../test/helpers'
import type { PlatformStatus } from '../../types/dashboard'

function platform(overrides: Partial<PlatformStatus> = {}): PlatformStatus {
  return {
    pf_id: '102*****89',
    appid: '102*****89',
    name: '主机器人',
    platform: 'qq_official',
    secret_set: true,
    source: 'compatibility',
    state: 'synced',
    scenes: [
      {
        scene: 'c2c',
        enabled: true,
        state: 'synced',
        item_count: 2,
        digest: 'c2c',
      },
    ],
    ...overrides,
  }
}

describe('PlatformStatusCard', () => {
  it('renders the platform, source and synced state', () => {
    const wrapper = mountView(PlatformStatusCard, {
      props: { platform: platform() },
    })

    expect(wrapper.text()).toContain('102*****89')
    expect(wrapper.text()).toContain('主机器人')
    expect(wrapper.find('[data-field="robot-title"]').text()).toBe('主机器人')
    expect(wrapper.text()).toContain('qq_official')
    expect(wrapper.text()).toContain('兼容性配置')
    expect(wrapper.text()).toContain('已同步')
    expect(wrapper.text()).toContain('已配置')
    expect(wrapper.text()).toContain('私聊')
  })

  it.each([
    ['pending', '待同步'],
    ['unknown', '尚未同步'],
    ['disabled', '同步已关闭'],
  ])('labels the %s state', (state, label) => {
    const wrapper = mountView(PlatformStatusCard, {
      props: { platform: platform({ state: state as PlatformStatus['state'] }) },
    })

    expect(wrapper.text()).toContain(label)
  })

  it('marks missing secrets', () => {
    const wrapper = mountView(PlatformStatusCard, {
      props: {
        platform: platform({ source: 'robot', secret_set: false }),
      },
    })

    expect(wrapper.text()).toContain('机器人')
    expect(wrapper.text()).toContain('未配置')
  })
})
