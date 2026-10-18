import { describe, expect, it, vi } from 'vitest'
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
    primary_color: '#3c96ca',
    secondary_color: '#2f86bd',
    qq_platforms: [],
    runtime_platforms: [],
    menu: [],
    limits: { top_level_max: 10, sub_items_max: 10 },
    ...overrides,
  }
}

async function loadView(options: { withBackend?: boolean } = {}) {
  const bridge = options.withBackend === false ? null : installBridge()
  vi.resetModules()
  const api = await import('../api/dashboard')
  const { default: SettingsView } = await import('./SettingsView.vue')

  return {
    bridge,
    api,
    async mount() {
      const wrapper = mountView(SettingsView)
      await waitUntil(() => vi.mocked(api.fetchConfig).mock.calls.length > 0)
      await flush()
      return wrapper
    },
  }
}

function saveButton(wrapper: ReturnType<typeof mountView>) {
  return wrapper.findAll('button').find((button) => button.text().trim() === '保存')
}

describe('SettingsView', () => {
  it('renders the current settings and about card', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('设置')
    expect(wrapper.text()).toContain('日志语言')
    expect(wrapper.text()).toContain('启动时同步私聊菜单')
    expect(wrapper.text()).toContain('主题配色')
    expect(wrapper.text()).toContain('主色')
    expect(wrapper.text()).toContain('辅助色')
    expect(wrapper.text()).toContain('v0.2.3')
    expect(wrapper.find('.qc-github-link').attributes('href')).toContain('github.com')
  })

  it('saves language and sync switch', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(configFixture({ sync_menu: false }))

    const wrapper = await mount()
    await wrapper.find('[data-field="settings-sync-menu"] input').setValue(false)
    await saveButton(wrapper)?.trigger('click')
    await flush()

    expect(api.saveConfig).toHaveBeenCalledWith({
      language: 'zh-CN',
      sync_menu: false,
      primary_color: '#3c96ca',
      secondary_color: '#2f86bd',
    })
    expect(wrapper.text()).toContain('设置已保存并生效')
  })

  it('shows save errors', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())
    vi.mocked(api.saveConfig).mockRejectedValue(new Error('save failed'))

    const wrapper = await mount()
    await saveButton(wrapper)?.trigger('click')
    await flush()

    expect(wrapper.text()).toContain('save failed')
  })

  it('saves normalized theme colors', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(
      configFixture({ primary_color: '#aabbcc', secondary_color: '#112233' }),
    )

    const wrapper = await mount()
    await wrapper.find('[data-field="settings-primary-color"] input').setValue(' #AABBCC ')
    await wrapper.find('[data-field="settings-secondary-color"] input').setValue('#112233')
    await saveButton(wrapper)?.trigger('click')
    await flush()

    expect(api.saveConfig).toHaveBeenCalledWith({
      language: 'zh-CN',
      sync_menu: true,
      primary_color: '#aabbcc',
      secondary_color: '#112233',
    })
  })

  it('disables saving when a theme color is invalid', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()
    await wrapper.find('[data-field="settings-primary-color"] input').setValue('red')
    await flush()

    expect(saveButton(wrapper)?.attributes('disabled')).toBeDefined()
    expect(api.saveConfig).not.toHaveBeenCalled()
  })

  it('shows load errors', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockRejectedValue(new Error('load failed'))

    const wrapper = await mount()

    expect(wrapper.text()).toContain('load failed')
  })

  it('disables saving in local mock mode', async () => {
    const { api, mount } = await loadView({ withBackend: false })
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('不能保存配置')
    expect(saveButton(wrapper)?.attributes('disabled')).toBeDefined()
  })
})
