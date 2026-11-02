import { describe, expect, it, vi } from 'vitest'
import { buttonByText, flush, loadDashboardView } from '../test/helpers'
import { statusFixture } from '../test/fixtures'

vi.mock('../api/dashboard', () => ({
  fetchStatus: vi.fn(),
  fetchConfig: vi.fn(),
  saveConfig: vi.fn(),
}))

function loadView(options: { withBackend?: boolean } = {}) {
  return loadDashboardView({
    api: () => import('../api/dashboard'),
    component: () => import('./StatusOverviewView.vue'),
    bridge:
      options.withBackend === false
        ? false
        : {
            subscribeSSE: vi.fn(async () => 'sub-1'),
            unsubscribeSSE: vi.fn(async () => ({})),
          },
    waitFor: (api) => () => vi.mocked(api.fetchStatus).mock.calls.length > 0,
  })
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
    ])
    expect(wrapper.text()).toContain('102*****89')
    expect(wrapper.text()).toContain('已同步')
    expect(wrapper.text()).not.toContain('场景状态')
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

    expect(wrapper.text()).toContain('同步会清理已启用场景中的旧内容')
  })

  it('shows the sync-disabled hint', async () => {
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
            source: 'compatibility',
            state: 'disabled',
          },
        ],
      }),
    )

    const wrapper = await mount()

    expect(wrapper.text()).toContain('插件只读取 QQ 私聊菜单')
    expect(wrapper.text()).not.toContain('AstrBot 平台配置')
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
    await buttonByText(wrapper, '刷新')?.trigger('click')
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
