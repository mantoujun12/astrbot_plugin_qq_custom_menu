import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { flush, installBridge, mountView, waitUntil } from '../test/helpers'
import type { PluginConfigResponse } from '../types/dashboard'

vi.mock('../api/dashboard', () => ({
  fetchStatus: vi.fn(),
  fetchConfig: vi.fn(),
  saveConfig: vi.fn(),
}))

function configFixture(overrides: Partial<PluginConfigResponse> = {}): PluginConfigResponse {
  return {
    plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
    language: 'zh-CN',
    sync_menu: true,
    qq_platforms: [
      {
        appid: '1023456789',
        platform: 'qq_official',
        secret_masked: 'ab*****yz',
        secret_set: true,
      },
    ],
    runtime_platforms: [],
    menu: [
      { type: 'send_message', name: '帮助', message: '/help', parent: '' },
      { type: 'menu', name: '更多', parent: '' },
      { type: 'link', name: '文档', link: 'https://docs.app', parent: '更多' },
    ],
    limits: { top_level_max: 10, sub_items_max: 10 },
    ...overrides,
  }
}

async function loadView(options: { withBackend?: boolean } = {}) {
  const bridge =
    options.withBackend === false
      ? null
      : installBridge({
          apiPost: vi.fn(async (endpoint: string) =>
            endpoint === 'sync' ? { started: true, busy: false } : configFixture(),
          ),
          subscribeSSE: vi.fn(async () => 'sub-1'),
          unsubscribeSSE: vi.fn(async () => ({})),
        })
  vi.resetModules()
  const api = await import('../api/dashboard')
  const { default: MenuView } = await import('./MenuView.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/status', name: 'status', component: { template: '<div />' } },
      { path: '/menu', name: 'menu', component: { template: '<div />' } },
      { path: '/:pathMatch(.*)*', redirect: '/status' },
    ],
  })
  await router.push('/menu')
  await router.isReady()

  return {
    bridge,
    api,
    router,
    async mount() {
      const wrapper = mountView(MenuView, { global: { plugins: [router] } })
      await waitUntil(() => vi.mocked(api.fetchConfig).mock.calls.length > 0)
      await flush()
      return wrapper
    },
  }
}

function saveButton(wrapper: ReturnType<typeof mountView>) {
  return wrapper.findAll('button').find((button) => button.text().trim() === '保存')
}

describe('MenuView', () => {
  it('loads and renders the menu tree', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('菜单配置')
    expect(wrapper.text()).toContain('帮助')
    expect(wrapper.text()).toContain('更多')
    expect(wrapper.text()).toContain('文档')
    expect(wrapper.text()).toContain('一级菜单 2/10')
  })

  it('saves the current menu and shows a notice', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(configFixture())

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
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()
    await wrapper.findAll('[aria-label="删除"]')[0].trigger('click')
    await saveButton(wrapper)?.trigger('click')
    await flush()

    const payload = vi.mocked(api.saveConfig).mock.calls[0][0]
    expect(payload.menu?.map((entry) => entry.name)).toEqual(['更多', '文档'])
  })

  it('adds a child through the dialog', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(configFixture())

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
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()
    const saveAndSync = wrapper
      .findAll('button')
      .find((button) => button.text().includes('保存并同步'))
    await saveAndSync?.trigger('click')
    await waitUntil(() => router.currentRoute.value.path === '/status')

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
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('不能保存配置')
    expect(saveButton(wrapper)?.attributes('disabled')).toBeDefined()
  })

  it('opens the add dialog for a top-level entry', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()
    const add = wrapper
      .findAll('button')
      .find((button) => button.text().includes('添加一级菜单'))
    await add?.trigger('click')
    await flush()

    expect(wrapper.findComponent({ name: 'MenuEntryDialog' }).props('modelValue')).toBe(true)
  })
})
