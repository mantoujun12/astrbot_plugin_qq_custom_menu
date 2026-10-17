import { describe, expect, it, vi } from 'vitest'
import { flush, installBridge, mountView, waitUntil } from '../test/helpers'
import type { StatusResponse } from '../types/dashboard'

vi.mock('../api/dashboard', () => ({
  fetchStatus: vi.fn(),
  fetchConfig: vi.fn(),
  saveConfig: vi.fn(),
}))

function statusFixture(overrides: Partial<StatusResponse> = {}): StatusResponse {
  return {
    plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
    ready: true,
    sync_menu: true,
    state: { available: true },
    platforms: [
      {
        pf_id: '102*****89',
        appid: '102*****89',
        platform: 'qq_official',
        secret_set: true,
        source: 'plugin',
        state: 'synced',
      },
    ],
    menu: {
      top_level: 2,
      sub_items: 1,
      total: 3,
      top_level_max: 10,
      sub_items_max: 10,
      digest: 'digest',
      items: [
        { type: 'send_message', name: '帮助', send_message: '/help' },
        {
          type: 'menu',
          name: '更多',
          sub_menu_items: [{ type: 'link', name: '文档', link: 'https://docs.app' }],
        },
      ],
    },
    ...overrides,
  }
}

async function loadView(options: { withBackend?: boolean } = {}) {
  const bridge =
    options.withBackend === false ? null : installBridge({
      subscribeSSE: vi.fn(async () => 'sub-1'),
      unsubscribeSSE: vi.fn(async () => ({})),
    })
  vi.resetModules()
  const api = await import('../api/dashboard')
  const { default: StatusOverviewView } = await import('./StatusOverviewView.vue')

  return {
    bridge,
    api,
    async mount() {
      const wrapper = mountView(StatusOverviewView)
      await waitUntil(() => vi.mocked(api.fetchStatus).mock.calls.length > 0)
      await flush()
      return wrapper
    },
  }
}

describe('StatusOverviewView', () => {
  it('loads the status and renders the overview', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchStatus).mockResolvedValue(statusFixture())

    const wrapper = await mount()

    expect(api.fetchStatus).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('状态概览')
    expect(wrapper.findAll('.qc-metric-value').map((node) => node.text())).toEqual([
      '1',
      '2',
      '1',
      '3',
    ])
    expect(wrapper.text()).toContain('102*****89')
    expect(wrapper.text()).toContain('已同步')
    expect(wrapper.text()).toContain('菜单预览')
    expect(wrapper.text()).toContain('文档')
  })

  it('shows the backend error instead of the cards', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchStatus).mockRejectedValue(new Error('status failed'))

    const wrapper = await mount()

    expect(wrapper.text()).toContain('获取状态失败')
    expect(wrapper.text()).toContain('status failed')
    expect(wrapper.findAll('.qc-metric-value')).toHaveLength(0)
  })

  it('points at the robots page when no platform is configured', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchStatus).mockResolvedValue(statusFixture({ platforms: [] }))

    const wrapper = await mount()

    expect(wrapper.text()).toContain('还没有可用的 QQ 平台')
    expect(wrapper.text()).not.toContain('102*****89')
  })

  it('warns when the menu is empty', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchStatus).mockResolvedValue(
      statusFixture({
        menu: {
          ...statusFixture().menu,
          top_level: 0,
          sub_items: 0,
          total: 0,
          items: [],
        },
      }),
    )

    const wrapper = await mount()

    expect(wrapper.text()).toContain('同步会清空 QQ 上已有的自定义菜单')
  })

  it('shows sync-disabled and fallback hints', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchStatus).mockResolvedValue(
      statusFixture({
        sync_menu: false,
        platforms: [
          {
            pf_id: 'abc***yz',
            appid: 'abc***yz',
            platform: 'qq_official',
            secret_set: true,
            source: 'astrbot',
            state: 'disabled',
          },
        ],
      }),
    )

    const wrapper = await mount()

    expect(wrapper.text()).toContain('插件只会读取 QQ 菜单')
    expect(wrapper.text()).toContain('当前平台凭证来自 AstrBot 平台配置')
  })

  it('labels mock data in local dev', async () => {
    const { api, mount } = await loadView({ withBackend: false })
    vi.mocked(api.fetchStatus).mockResolvedValue(statusFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('展示的是 mock 数据')
  })

  it('refreshes with refresh=1', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchStatus).mockResolvedValue(statusFixture())

    const wrapper = await mount()
    const refresh = wrapper
      .findAll('button')
      .find((button) => button.text().includes('刷新'))
    await refresh?.trigger('click')
    await flush()

    expect(api.fetchStatus).toHaveBeenLastCalledWith({ refresh: true })
  })

  it('reloads after the sync panel finishes', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchStatus).mockResolvedValue(statusFixture())

    const wrapper = await mount()
    wrapper.findComponent({ name: 'SyncPanel' }).vm.$emit('finished')
    await flush()

    expect(api.fetchStatus).toHaveBeenCalledTimes(2)
  })
})
