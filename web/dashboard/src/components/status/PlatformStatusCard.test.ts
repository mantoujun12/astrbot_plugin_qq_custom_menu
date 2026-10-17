import { describe, expect, it } from 'vitest'
import PlatformStatusCard from './PlatformStatusCard.vue'
import { mountView } from '../../test/helpers'
import type { PlatformStatus } from '../../types/dashboard'

function platform(overrides: Partial<PlatformStatus> = {}): PlatformStatus {
  return {
    pf_id: '102*****89',
    appid: '102*****89',
    platform: 'qq_official',
    secret_set: true,
    source: 'plugin',
    state: 'synced',
    ...overrides,
  }
}

describe('PlatformStatusCard', () => {
  it('renders the platform, source and synced state', () => {
    const wrapper = mountView(PlatformStatusCard, {
      props: { platform: platform() },
    })

    expect(wrapper.text()).toContain('102*****89')
    expect(wrapper.text()).toContain('qq_official')
    expect(wrapper.text()).toContain('插件配置')
    expect(wrapper.text()).toContain('已同步')
    expect(wrapper.text()).toContain('已配置')
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

  it('marks missing secrets and fallback platforms', () => {
    const wrapper = mountView(PlatformStatusCard, {
      props: {
        platform: platform({ source: 'astrbot', secret_set: false }),
      },
    })

    expect(wrapper.text()).toContain('AstrBot 平台配置')
    expect(wrapper.text()).toContain('未配置')
  })
})
