import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { flush, installBridge, mountView, waitUntil } from '../test/helpers'
import type { RobotConfigResponse } from '../types/robotConfig'

vi.mock('../api/robots', () => ({
  fetchRobots: vi.fn(),
  saveRobots: vi.fn(),
  importLegacyRobots: vi.fn(),
}))

vi.mock('../api/dashboard', () => ({
  fetchStatus: vi.fn(),
  fetchConfig: vi.fn(),
  saveConfig: vi.fn(),
}))

function responseFixture(): RobotConfigResponse {
  return {
    version: 1,
    robots: [
      {
        id: 'robot-1',
        name: '主机器人',
        appid: '1023456789',
        platform: 'qq_official',
        secret_masked: 'ab***yz',
        secret_set: true,
        scenes: {
          c2c: {
            enabled: true,
            items: [
              { type: 'send_message', name: '帮助', message: '/help', parent: '' },
              { type: 'menu', name: '更多', parent: '' },
              {
                type: 'link',
                name: '文档',
                link: 'https://docs.app',
                parent: '更多',
              },
            ],
          },
        },
      },
    ],
    available_scenes: ['c2c'],
    menu_limits: { top_level_max: 10, sub_items_max: 5 },
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
  const robotsApi = await import('../api/robots')
  const dashboardApi = await import('../api/dashboard')
  const { default: RobotsView } = await import('./RobotsView.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/status', name: 'status', component: { template: '<div />' } },
      { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
    ],
  })
  await router.push('/robots')
  await router.isReady()

  return {
    bridge,
    robotsApi,
    dashboardApi,
    async mount() {
      const wrapper = mountView(RobotsView, {
        global: {
          plugins: [router],
          stubs: {
            VDialog: { template: '<div class="dialog-stub"><slot /></div>' },
          },
        },
      })
      await waitUntil(() => vi.mocked(robotsApi.fetchRobots).mock.calls.length > 0)
      await flush()
      return wrapper
    },
  }
}

function saveButton(wrapper: ReturnType<typeof mountView>) {
  return wrapper.findAll('button').find((button) => button.text().trim() === '保存')
}

describe('RobotsView', () => {
  it('renders each robot private-chat menu', async () => {
    const { robotsApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(responseFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('机器人')
    expect(wrapper.text()).toContain('主机器人')
    expect(wrapper.text()).toContain('私聊')
    expect(wrapper.text()).toContain('帮助')
    const listPane = wrapper.find('[data-pane="list"]')
    const editorPane = wrapper.find('[data-pane="editor"]')
    expect(listPane.element.parentElement).toBe(editorPane.element.parentElement)
    expect(
      listPane.element.parentElement?.classList.contains('qc-robots-shell'),
    ).toBe(true)
    expect(wrapper.find('[data-field="robots-divider-desktop"]').exists()).toBe(true)
  })

  it('saves private-chat menu data', async () => {
    const { robotsApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(responseFixture())
    vi.mocked(robotsApi.saveRobots).mockResolvedValue({
      ...responseFixture(),
      version: 2,
    })

    const wrapper = await mount()
    await saveButton(wrapper)?.trigger('click')
    await flush()

    const payload = vi.mocked(robotsApi.saveRobots).mock.calls[0][0]
    expect(payload.version).toBe(1)
    expect(payload.robots[0].scenes.c2c.items.map((item) => item.name)).toEqual([
      '帮助',
      '更多',
      '文档',
    ])
    expect(wrapper.text()).toContain('机器人配置已保存')
  })

  it('creates a new robot from the dialog', async () => {
    const { robotsApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(responseFixture())

    const wrapper = await mount()
    const addRobot = wrapper
      .findAll('button')
      .find((button) => button.text().includes('新增机器人'))
    await addRobot?.trigger('click')
    await flush()

    await wrapper.find('[data-field="create-name"] input').setValue('二号机器人')
    await wrapper.find('[data-field="create-appid"] input').setValue('987654321')
    await wrapper.find('[data-field="create-secret"] input').setValue('secret')
    const create = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === '创建')
    await create?.trigger('click')
    await flush()

    expect(wrapper.text()).toContain('二号机器人')
    expect(wrapper.text()).toContain('保存后才会写入配置')
  })

  it('disables saving in local mock mode', async () => {
    const { robotsApi, mount } = await loadView({ withBackend: false })
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(responseFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('不能保存配置')
    expect(saveButton(wrapper)?.attributes('disabled')).toBeDefined()
    const importButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('从兼容配置导入'))
    expect(importButton?.attributes('disabled')).toBeDefined()
  })

  it('imports legacy AppIDs through the dedicated endpoint', async () => {
    const { robotsApi, dashboardApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(responseFixture())
    vi.mocked(dashboardApi.fetchConfig).mockResolvedValue({
      plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
      language: 'zh-CN',
      sync_menu: true,
      primary_color: '#3c96ca',
      secondary_color: '#2f86bd',
      qq_platforms: [
        {
          appid: '987654321',
          platform: 'qq_official',
          secret_masked: 'ab***yz',
          secret_set: true,
        },
      ],
      runtime_platforms: [],
      menu: [],
      limits: { top_level_max: 10, sub_items_max: 5 },
    })
    vi.mocked(robotsApi.importLegacyRobots).mockResolvedValue({
      ...responseFixture(),
      version: 2,
    })

    const wrapper = await mount()
    const open = wrapper
      .findAll('button')
      .find((button) => button.text().includes('从兼容配置导入'))
    await open?.trigger('click')
    await flush()
    expect(
      wrapper.find('[data-field="legacy-appids"] textarea').element,
    ).toHaveProperty('value', '987654321')
    const confirm = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === '导入')
    await confirm?.trigger('click')
    await flush()

    expect(robotsApi.importLegacyRobots).toHaveBeenCalledWith(['987654321'], 1)
    expect(wrapper.text()).toContain('已从兼容配置导入机器人')
  })

  it('keeps unsaved drafts when importing legacy robots', async () => {
    const { robotsApi, dashboardApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(responseFixture())
    vi.mocked(dashboardApi.fetchConfig).mockResolvedValue({
      plugin: { name: 'astrbot_plugin_qq_custom_menu', version: 'v0.2.3' },
      language: 'zh-CN',
      sync_menu: true,
      primary_color: '#3c96ca',
      secondary_color: '#2f86bd',
      qq_platforms: [
        {
          appid: '987654321',
          platform: 'qq_official',
          secret_masked: 'ab***yz',
          secret_set: true,
        },
      ],
      runtime_platforms: [],
      menu: [],
      limits: { top_level_max: 10, sub_items_max: 5 },
    })
    vi.mocked(robotsApi.importLegacyRobots).mockResolvedValue({
      ...responseFixture(),
      version: 2,
      robots: [
        ...responseFixture().robots,
        {
          id: 'robot-2',
          name: '导入机器人',
          appid: '987654321',
          platform: 'qq_official',
          secret_masked: 'cd***ef',
          secret_set: true,
          scenes: {
            c2c: {
              enabled: true,
              items: [
                { type: 'send_message', name: '旧版菜单', message: '/legacy', parent: '' },
              ],
            },
          },
        },
      ],
    })
    vi.mocked(robotsApi.saveRobots).mockResolvedValue({
      ...responseFixture(),
      version: 3,
    })

    const wrapper = await mount()
    const addRobot = wrapper
      .findAll('button')
      .find((button) => button.text().includes('新增机器人'))
    await addRobot?.trigger('click')
    await flush()
    await wrapper.find('[data-field="create-name"] input').setValue('草稿机器人')
    await wrapper.find('[data-field="create-appid"] input').setValue('111222333')
    await wrapper.find('[data-field="create-secret"] input').setValue('secret')
    const create = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === '创建')
    await create?.trigger('click')
    await flush()

    const open = wrapper
      .findAll('button')
      .find((button) => button.text().includes('从兼容配置导入'))
    await open?.trigger('click')
    await flush()
    const confirm = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === '导入')
    await confirm?.trigger('click')
    await flush()

    expect(wrapper.text()).toContain('草稿机器人')
    expect(wrapper.text()).toContain('导入机器人')

    await saveButton(wrapper)?.trigger('click')
    await flush()

    const payload = vi.mocked(robotsApi.saveRobots).mock.calls[0][0]
    expect(payload.version).toBe(2)
    expect(payload.robots.map((robot) => robot.appid)).toEqual([
      '1023456789',
      '111222333',
      '987654321',
    ])
  })

  it('deletes a selected robot after confirmation', async () => {
    const { robotsApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(responseFixture())

    const wrapper = await mount()
    const remove = wrapper
      .findAll('button')
      .find((button) => button.text().includes('删除机器人配置'))
    await remove?.trigger('click')
    await flush()
    const confirm = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === '确认删除')
    await confirm?.trigger('click')
    await flush()

    expect(wrapper.text()).toContain('还没有机器人')
    expect(wrapper.text()).toContain('保存后才会写入配置')
  })

})
