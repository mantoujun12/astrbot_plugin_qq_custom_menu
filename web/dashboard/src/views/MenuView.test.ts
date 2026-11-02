import { describe, expect, it, vi } from 'vitest'
import {
  buttonByText,
  flush,
  loadDashboardView,
  saveButton,
  waitUntil,
} from '../test/helpers'
import { pluginConfigFixture } from '../test/fixtures'

vi.mock('../api/dashboard', () => ({
  fetchStatus: vi.fn(),
  fetchConfig: vi.fn(),
  saveConfig: vi.fn(),
}))

const ROUTES = [
  { path: '/status', name: 'status', component: { template: '<div />' } },
  { path: '/menu', name: 'menu', component: { template: '<div />' } },
  { path: '/:pathMatch(.*)*', redirect: '/status' },
]

function loadView(options: { withBackend?: boolean } = {}) {
  return loadDashboardView({
    api: () => import('../api/dashboard'),
    component: () => import('./MenuView.vue'),
    bridge:
      options.withBackend === false
        ? false
        : {
            apiPost: vi.fn(async (endpoint: string) =>
              endpoint === 'sync' ? { started: true, busy: false } : pluginConfigFixture(),
            ),
            subscribeSSE: vi.fn(async () => 'sub-1'),
            unsubscribeSSE: vi.fn(async () => ({})),
          },
    routes: ROUTES,
    initial: '/menu',
    waitFor: (api) => () => vi.mocked(api.fetchConfig).mock.calls.length > 0,
  })
}

describe('MenuView', () => {
  it('loads and renders the menu tree', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('菜单配置')
    expect(wrapper.text()).toContain('帮助')
    expect(wrapper.text()).toContain('更多')
    expect(wrapper.text()).toContain('文档')
    expect(wrapper.text()).toContain('一级菜单 2/10')
  })

  it('saves the current menu and shows a notice', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()
    await saveButton(wrapper)?.trigger('click')
    await flush()

    expect(api.saveConfig).toHaveBeenCalledWith({
      menu: [
        { type: 'send_message', name: '帮助', parent: '', message: '/help' },
        { type: 'menu', name: '更多', parent: '' },
        { type: 'link', name: '文档', parent: '更多', link: 'https://docs.app' },
      ],
    })
    expect(wrapper.text()).toContain('菜单已保存并生效')
  })

  it('deletes an entry before saving', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()
    await wrapper.findAll('[aria-label="删除"]')[0].trigger('click')
    await saveButton(wrapper)?.trigger('click')
    await flush()

    const payload = vi.mocked(api.saveConfig).mock.calls[0][0]
    expect(payload.menu?.map((entry) => entry.name)).toEqual(['更多', '文档'])
  })

  it('adds a child through the dialog', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()
    await wrapper.find('[aria-label="添加子项"]').trigger('click')
    await flush()

    const dialog = wrapper.findComponent({ name: 'MenuEntryDialog' })
    expect(dialog.props('modelValue')).toBe(true)
    expect(dialog.props('parent')).toBe('更多')

    dialog.vm.$emit('save', {
      type: 'send_message',
      name: '关于',
      message: '/about',
      parent: '更多',
    })
    await flush()
    await saveButton(wrapper)?.trigger('click')
    await flush()

    const payload = vi.mocked(api.saveConfig).mock.calls[0][0]
    expect(payload.menu?.map((entry) => entry.name)).toEqual(['帮助', '更多', '文档', '关于'])
  })

  it('saves and syncs, then jumps to the status page', async () => {
    const { api, bridge, router, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()
    await buttonByText(wrapper, '保存并同步')?.trigger('click')
    await waitUntil(() => router?.currentRoute.value.path === '/status')

    expect(bridge?.apiPost).toHaveBeenCalledWith('sync')
  })

  it('shows load errors', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockRejectedValue(new Error('load failed'))

    const wrapper = await mount()

    expect(wrapper.text()).toContain('load failed')
  })

  it('disables editing in local mock mode', async () => {
    const { api, mount } = await loadView({ withBackend: false })
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('不能保存配置')
    expect(saveButton(wrapper)?.attributes('disabled')).toBeDefined()
  })

  it('opens the add dialog for a top-level entry', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(pluginConfigFixture())

    const wrapper = await mount()
    await buttonByText(wrapper, '添加一级菜单')?.trigger('click')
    await flush()

    expect(wrapper.findComponent({ name: 'MenuEntryDialog' }).props('modelValue')).toBe(true)
  })
})
