import { describe, expect, it, vi } from 'vitest'
import AppShell from './AppShell.vue'
import { resolvePageTitle } from './useAppShell'
import { installBridge, makeRouter, mountView, waitUntil } from '../test/helpers'

const ROUTES = [{ path: '/:pathMatch(.*)*', component: { template: '<div>page</div>' } }]

async function mountShell() {
  vi.resetModules()
  installBridge({
    getContext: vi.fn(() => ({ pageTitle: 'Host title', isDark: false })),
    ready: vi.fn(async () => ({ pageTitle: 'Host title', isDark: false })),
  })
  const router = await makeRouter(ROUTES, '/status')
  const wrapper = mountView(AppShell, { global: { plugins: [router] } })
  await waitUntil(() => wrapper.text().includes('Host title'))
  return wrapper
}

describe('AppShell', () => {
  it('renders the host title and navigates between views', async () => {
    const wrapper = await mountShell()

    expect(wrapper.text()).toContain('Host title')
    expect(wrapper.text()).toContain('page')
    expect(wrapper.text()).toContain('状态概览')
  })

  it('collapses the sidebar on wide screens', async () => {
    const wrapper = await mountShell()

    const toggle = wrapper.find('[aria-label="收起侧边栏"]')
    expect(toggle.exists()).toBe(true)
    await toggle.trigger('click')
    await waitUntil(() => wrapper.find('[aria-label="展开侧边栏"]').exists())

    expect(wrapper.text()).not.toContain('Host title')
  })

  it('does not treat the raw dashboard view name as the localized title', () => {
    expect(resolvePageTitle('dashboard', undefined, '自定义菜单')).toBe(
      '自定义菜单',
    )
    expect(resolvePageTitle('views.dashboard', undefined, 'Fallback')).toBe(
      'Fallback',
    )
    expect(resolvePageTitle('pages.dashboard', 'Plugin title', 'Fallback')).toBe(
      'Plugin title',
    )
    expect(resolvePageTitle('Host title', 'Plugin name', 'Fallback')).toBe(
      'Host title',
    )
  })
})
