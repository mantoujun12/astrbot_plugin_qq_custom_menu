import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { flush, installBridge, mountView, waitUntil } from '../test/helpers'
import type { PluginConfigResponse } from '../types/dashboard'

vi.mock('../api/dashboard', () => ({
  fetchStatus: vi.fn(),
  fetchConfig: vi.fn(),
  saveConfig: vi.fn(),
}))

function configFixture(): PluginConfigResponse {
  return {
    plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
    language: 'zh-CN',
    sync_menu: true,
    qq_platforms: [
      {
        appid: '1023456789',
        platform: 'qq_official',
        secret_masked: 'ab***yz',
        secret_set: true,
      },
    ],
    runtime_platforms: [],
    menu: [
      { type: 'send_message', name: '帮助', message: '/help', parent: '' },
      { type: 'menu', name: '更多', parent: '' },
      {
        type: 'link',
        name: '文档',
        link: 'https://docs.app',
        parent: '更多',
      },
    ],
    limits: { top_level_max: 10, sub_items_max: 5 },
  }
}

async function loadView(options: { withBackend?: boolean } = {}) {
  const bridge =
    options.withBackend === false
      ? null
      : installBridge({
          subscribeSSE: vi.fn(async () => 'sub-1'),
          unsubscribeSSE: vi.fn(async () => ({})),
        })
  vi.resetModules()
  const api = await import('../api/dashboard')
  const { default: CompatibilityView } = await import('./CompatibilityView.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/status', name: 'status', component: { template: '<div />' } },
      { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
    ],
  })
  await router.push('/compatibility')
  await router.isReady()

  return {
    bridge,
    api,
    async mount() {
      const wrapper = mountView(CompatibilityView, {
        global: { plugins: [router] },
      })
      await waitUntil(() => vi.mocked(api.fetchConfig).mock.calls.length > 0)
      await flush()
      return wrapper
    },
  }
}

function saveButton(wrapper: ReturnType<typeof mountView>) {
  return wrapper.findAll('button').find((button) => button.text().trim() === '保存')
}

describe('CompatibilityView', () => {
  it('renders the legacy platform and menu', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

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
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(configFixture())

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
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()
    const add = wrapper
      .findAll('button')
      .find((button) => button.text().includes('添加平台'))
    await add?.trigger('click')
    await flush()

    expect(wrapper.findAll('[data-field="platform-appid"] input')).toHaveLength(2)
  })

  it('disables saving in local mock mode', async () => {
    const { api, mount } = await loadView({ withBackend: false })
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('不能保存配置')
    expect(saveButton(wrapper)?.attributes('disabled')).toBeDefined()
  })

  it('rejects an empty AppID before saving', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()
    await wrapper.find('[data-field="platform-appid"] input').setValue('')
    await saveButton(wrapper)?.trigger('click')
    await flush()

    expect(wrapper.text()).toContain('缺少 AppID')
    expect(api.saveConfig).not.toHaveBeenCalled()
  })

  it('removes a platform and a legacy menu entry before saving', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())
    vi.mocked(api.saveConfig).mockResolvedValue({
      ...configFixture(),
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
