import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { flush, installBridge, mountView, waitUntil } from './test/helpers'

vi.mock('./api/dashboard', () => ({
  fetchStatus: vi.fn(async () => ({
    plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
    ready: true,
    sync_menu: true,
    state: { available: true },
    platforms: [],
    menu: {
      top_level: 0,
      sub_items: 0,
      total: 0,
      top_level_max: 10,
      sub_items_max: 10,
      digest: '',
      items: [],
    },
  })),
  fetchConfig: vi.fn(),
  saveConfig: vi.fn(),
}))

describe('App', () => {
  it('mounts the application shell and shows the navigation', async () => {
    vi.resetModules()
    installBridge()
    const { default: App } = await import('./App.vue')
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'status', component: { template: '<div>status</div>' } },
        { path: '/:pathMatch(.*)*', redirect: '/' },
      ],
    })
    await router.push('/')
    await router.isReady()

    const wrapper = mountView(App, { global: { plugins: [router] } })
    await flush()
    await waitUntil(() => wrapper.text().includes('状态概览'))

    expect(wrapper.find('.v-application').exists()).toBe(true)
    expect(wrapper.text()).toContain('机器人')
    expect(wrapper.text()).toContain('日志')
    expect(wrapper.text()).toContain('兼容性')
    expect(wrapper.text()).toContain('设置')
  })
})
