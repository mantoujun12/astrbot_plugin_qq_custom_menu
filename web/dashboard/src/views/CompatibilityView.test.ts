import { describe, expect, it, vi } from 'vitest'
import {
  buttonByText,
  flush,
  loadDashboardView,
  saveButton,
} from '../test/helpers'
import { pluginConfigFixture } from '../test/fixtures'

vi.mock('../api/dashboard', () => ({
  fetchStatus: vi.fn(),
  fetchConfig: vi.fn(),
  saveConfig: vi.fn(),
}))

const ROUTES = [
  { path: '/status', name: 'status', component: { template: '<div />' } },
  { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
]

function loadView(options: { withBackend?: boolean } = {}) {
  return loadDashboardView({
    api: () => import('../api/dashboard'),
    component: () => import('./CompatibilityView.vue'),
    bridge:
      options.withBackend === false
        ? false
        : {
            subscribeSSE: vi.fn(async () => 'sub-1'),
            unsubscribeSSE: vi.fn(async () => ({})),
          },
    routes: ROUTES,
    initial: '/compatibility',
    waitFor: (api) => () => vi.mocked(api.fetchConfig).mock.calls.length > 0,
  })
}

describe('CompatibilityView', () => {
  it('renders the legacy platform and menu', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('兼容性配置')
    expect(
      wrapper.find('[data-field="platform-appid"] input').element,
    ).toHaveProperty('value', '1023456789')
    expect(wrapper.text()).toContain('帮助')
    expect(wrapper.text()).toContain('文档')
  })

  it('saves compatibility platforms and menu together', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()
    await saveButton(wrapper)?.trigger('click')
    await flush()

    expect(api.saveConfig).toHaveBeenCalledWith({
      qq_platforms: [
        { appid: '1023456789', secret: '', platform: 'qq_official' },
      ],
      menu: [
        { type: 'send_message', name: '帮助', parent: '', message: '/help' },
        { type: 'menu', name: '更多', parent: '' },
        { type: 'link', name: '文档', parent: '更多', link: 'https://docs.app' },
      ],
    })
    expect(wrapper.text()).toContain('兼容性配置已保存')
  })

  it('adds a compatibility platform', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()
    await buttonByText(wrapper, '添加平台')?.trigger('click')
    await flush()

    expect(wrapper.findAll('[data-field="platform-appid"] input')).toHaveLength(2)
  })

  it('disables saving in local mock mode', async () => {
    const { api, mount } = await loadView({ withBackend: false })
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('不能保存配置')
    expect(saveButton(wrapper)?.attributes('disabled')).toBeDefined()
  })

  it('rejects an empty AppID before saving', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()
    await wrapper.find('[data-field="platform-appid"] input').setValue('')
    await saveButton(wrapper)?.trigger('click')
    await flush()

    expect(wrapper.text()).toContain('缺少 AppID')
    expect(api.saveConfig).not.toHaveBeenCalled()
  })

  it('removes a platform and a legacy menu entry before saving', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())
    vi.mocked(api.saveConfig).mockResolvedValue({
      ...pluginConfigFixture(),
      qq_platforms: [],
      menu: [{ type: 'send_message', name: '帮助', message: '/help', parent: '' }],
    })

    const wrapper = await mount()
    await wrapper.findAll('[aria-label="删除"]')[0].trigger('click')
    await wrapper.findAll('[aria-label="删除"]')[1].trigger('click')
    await saveButton(wrapper)?.trigger('click')
    await flush()

    const payload = vi.mocked(api.saveConfig).mock.calls[0][0]
    expect(payload.qq_platforms).toEqual([])
    expect(payload.menu?.map((entry) => entry.name)).toEqual(['帮助'])
  })
})
