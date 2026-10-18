import { describe, expect, it } from 'vitest'
import { mdiCogOutline, mdiHistory } from '@mdi/js'
import { createMemoryHistory, createRouter } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import NavItem from './NavItem.vue'
import { mountView } from '../../test/helpers'

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }],
  })
}

describe('AppSidebar', () => {
  it('renders navigation, title and version', async () => {
    const router = makeRouter()
    await router.push('/status')
    await router.isReady()

    const wrapper = mountView(AppSidebar, {
      props: {
        title: '自定义菜单',
        toggleIcon: mdiCogOutline,
        toggleLabel: '收起侧边栏',
      },
      global: { plugins: [router] },
    })

    expect(wrapper.text()).toContain('自定义菜单')
    expect(wrapper.text()).toContain('状态概览')
    expect(wrapper.text()).toContain('机器人')
    expect(wrapper.text()).toContain('兼容性')
    expect(wrapper.text()).toContain('设置')
    expect(wrapper.text()).toContain('v0.3.0')

    expect(wrapper.find('[data-nav-section="main"]').text()).not.toContain('兼容性')
    expect(wrapper.find('[data-nav-section="bottom"]').text()).toContain('兼容性')
    const compatibility = wrapper
      .findAllComponents(NavItem)
      .find((item) => item.props('to') === '/compatibility')
    expect(compatibility?.props('icon')).toBe(mdiHistory)
  })

  it('emits toggle when the brand button is clicked', async () => {
    const router = makeRouter()
    await router.push('/status')
    await router.isReady()

    const wrapper = mountView(AppSidebar, {
      props: {
        title: '自定义菜单',
        toggleIcon: mdiCogOutline,
        toggleLabel: '收起侧边栏',
      },
      global: { plugins: [router] },
    })

    await wrapper.find('[aria-label="收起侧边栏"]').trigger('click')

    expect(wrapper.emitted('toggle')).toHaveLength(1)
  })

  it('hides the title and version in rail mode', async () => {
    const router = makeRouter()
    await router.push('/status')
    await router.isReady()

    const wrapper = mountView(AppSidebar, {
      props: {
        rail: true,
        title: '自定义菜单',
        toggleIcon: mdiCogOutline,
        toggleLabel: '展开侧边栏',
      },
      global: { plugins: [router] },
    })

    expect(wrapper.text()).not.toContain('自定义菜单')
    expect(wrapper.text()).not.toContain('v0.3.0')
  })
})
