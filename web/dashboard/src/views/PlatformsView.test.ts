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
    qq_platforms: [
      {
        appid: '1023456789',
        platform: 'qq_official',
        secret_masked: 'ab*****yz',
        secret_set: true,
      },
    ],
    runtime_platforms: [
      {
        pf_id: '102*****89',
        appid: '102*****89',
        platform: 'qq_official',
        secret_set: true,
        source: 'plugin',
      },
    ],
    menu: [],
    limits: { top_level_max: 10, sub_items_max: 10 },
    ...overrides,
  }
}

async function loadView(options: { withBackend?: boolean } = {}) {
  const bridge =
    options.withBackend === false ? null : installBridge()
  vi.resetModules()
  const api = await import('../api/dashboard')
  const { default: PlatformsView } = await import('./PlatformsView.vue')

  return {
    bridge,
    api,
    async mount() {
      const wrapper = mountView(PlatformsView)
      await waitUntil(() => vi.mocked(api.fetchConfig).mock.calls.length > 0)
      await flush()
      return wrapper
    },
  }
}

function saveButton(wrapper: ReturnType<typeof mountView>) {
  return wrapper.findAll('button').find((button) => button.text().trim() === '保存')
}

describe('PlatformsView', () => {
  it('renders saved and effective platforms', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('机器人')
    expect(wrapper.text()).toContain('1023456789')
    expect(
      wrapper.find('[data-field="platform-secret"] input').attributes('placeholder'),
    ).toContain('ab*****yz')
    expect(wrapper.text()).toContain('当前生效的平台')
  })

  it('adds a robot and saves credentials', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()
    await wrapper.find('[data-field="platform-add"]').trigger('click')
    await flush()

    const appids = wrapper.findAll('[data-field="platform-appid"] input')
    const secrets = wrapper.findAll('[data-field="platform-secret"] input')
    expect(appids).toHaveLength(2)

    await appids[1].setValue('987654321')
    await secrets[1].setValue('new-secret')
    await saveButton(wrapper)?.trigger('click')
    await flush()

    expect(api.saveConfig).toHaveBeenCalledWith({
      qq_platforms: [
        { appid: '1023456789', secret: '', platform: 'qq_official' },
        { appid: '987654321', secret: 'new-secret', platform: 'qq_official' },
      ],
    })
    expect(wrapper.text()).toContain('机器人凭证已保存并生效')
  })

  it('removes a robot before saving', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())
    vi.mocked(api.saveConfig).mockResolvedValue(configFixture({ qq_platforms: [] }))

    const wrapper = await mount()
    await wrapper.find('[aria-label="删除"]').trigger('click')
    await saveButton(wrapper)?.trigger('click')
    await flush()

    expect(api.saveConfig).toHaveBeenCalledWith({ qq_platforms: [] })
  })

  it('rejects an empty appid', async () => {
    const { api, mount } = await loadView()
    vi.mocked(api.fetchConfig).mockResolvedValue(configFixture())

    const wrapper = await mount()
    await wrapper.find('[data-field="platform-appid"] input').setValue('')
    await saveButton(wrapper)?.trigger('click')
    await flush()

    expect(wrapper.text()).toContain('缺少 AppID')
    expect(api.saveConfig).not.toHaveBeenCalled()
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
})
