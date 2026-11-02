import { describe, expect, it, vi } from 'vitest'
import {
  buttonByText,
  flush,
  loadDashboardView,
  saveButton,
} from '../test/helpers'
import { pluginConfigFixture, robotFixture, robotResponseFixture } from '../test/fixtures'
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

const ROUTES = [
  { path: '/status', name: 'status', component: { template: '<div />' } },
  { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
]

function twoRobotResponse(): RobotConfigResponse {
  const response = robotResponseFixture()
  response.robots.push(
    robotFixture({
      id: 'robot-2',
      name: '备用机器人',
      appid: '987654321',
      secret_masked: 'cd***ef',
      scenes: { c2c: { enabled: true, items: [] } },
    }),
  )
  return response
}

async function loadView(options: { withBackend?: boolean } = {}) {
  const loaded = await loadDashboardView({
    api: async () => ({
      robots: await import('../api/robots'),
      dashboard: await import('../api/dashboard'),
    }),
    component: () => import('./RobotsView.vue'),
    bridge:
      options.withBackend === false
        ? false
        : {
            subscribeSSE: vi.fn(async () => 'sub-1'),
            unsubscribeSSE: vi.fn(async () => ({})),
          },
    routes: ROUTES,
    initial: '/robots',
    stubs: { VDialog: { template: '<div class="dialog-stub"><slot /></div>' } },
    waitFor: (api) => () => vi.mocked(api.robots.fetchRobots).mock.calls.length > 0,
  })
  return {
    ...loaded,
    robotsApi: loaded.api.robots,
    dashboardApi: loaded.api.dashboard,
  }
}

describe('RobotsView', () => {
  it('renders each robot private-chat menu', async () => {
    const { robotsApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(robotResponseFixture())

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
    expect(wrapper.find('[data-field="robot-select"]').exists()).toBe(true)
    expect(wrapper.find('[data-field="robots-divider-desktop"]').exists()).toBe(true)
  })

  it('switches robots through the compact selector', async () => {
    const { robotsApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(twoRobotResponse())

    const wrapper = await mount()
    const robotSelect = wrapper
      .findAllComponents({ name: 'VSelect' })
      .find((component) => component.attributes('data-field') === 'robot-select')

    expect(robotSelect).toBeDefined()
    await wrapper.find('[data-field="robot-select"] .v-field').trigger('mousedown')
    await flush()

    expect(document.body.textContent).toContain(
      '987654321 · 启用场景 1 个，菜单条目 0 条。',
    )

    robotSelect?.vm.$emit('update:modelValue', 'robot:robot-2')
    await flush()

    expect(
      wrapper.find('[data-field="robot-name"] input').element,
    ).toHaveProperty('value', '备用机器人')
  })

  it('switches robots through the desktop cards', async () => {
    const { robotsApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(twoRobotResponse())

    const wrapper = await mount()
    const cards = wrapper.findAll('[data-pane="list"] .qc-config-item')
    expect(cards).toHaveLength(2)

    await cards[1].trigger('click')
    await flush()
    expect(
      wrapper.find('[data-field="robot-name"] input').element,
    ).toHaveProperty('value', '备用机器人')

    await cards[0].trigger('keydown', { key: 'Enter' })
    await flush()
    expect(
      wrapper.find('[data-field="robot-name"] input').element,
    ).toHaveProperty('value', '主机器人')

    await cards[1].trigger('keydown', { key: ' ' })
    await flush()
    expect(
      wrapper.find('[data-field="robot-name"] input').element,
    ).toHaveProperty('value', '备用机器人')
  })

  it('renders fallback metadata for an incomplete robot draft', async () => {
    const { robotsApi, mount } = await loadView()
    const response = robotResponseFixture()
    response.robots.push(
      robotFixture({
        id: '',
        name: '',
        appid: '',
        secret_masked: '',
        secret_set: false,
        scenes: { c2c: { enabled: true, items: [] } },
      }),
    )
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(response)

    const wrapper = await mount()
    const robotSelect = wrapper
      .findAllComponents({ name: 'VSelect' })
      .find((component) => component.attributes('data-field') === 'robot-select')
    await wrapper.find('[data-field="robot-select"] .v-field').trigger('mousedown')
    await flush()

    expect(document.body.textContent).toContain('未命名机器人')
    expect(document.body.textContent).toContain(
      '— · 启用场景 1 个，菜单条目 0 条。',
    )

    const slot = robotSelect?.vm.$slots.item
    const nodes = slot?.({
      props: { value: 'missing', title: 'missing' },
      index: 0,
    }) as Array<{ props?: { subtitle?: string } }>
    expect(nodes[0]?.props?.subtitle).toBe('')
  })

  it('saves private-chat menu data', async () => {
    const { robotsApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(robotResponseFixture())
    vi.mocked(robotsApi.saveRobots).mockResolvedValue({
      ...robotResponseFixture(),
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
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(robotResponseFixture())

    const wrapper = await mount()
    await buttonByText(wrapper, '新增机器人')?.trigger('click')
    await flush()

    await wrapper.find('[data-field="create-name"] input').setValue('二号机器人')
    await wrapper.find('[data-field="create-appid"] input').setValue('987654321')
    await wrapper.find('[data-field="create-secret"] input').setValue('secret')
    await buttonByText(wrapper, '创建', true)?.trigger('click')
    await flush()

    expect(wrapper.text()).toContain('二号机器人')
    expect(wrapper.text()).toContain('保存后才会写入配置')
  })

  it('disables saving in local mock mode', async () => {
    const { robotsApi, mount } = await loadView({ withBackend: false })
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(robotResponseFixture())

    const wrapper = await mount()

    expect(wrapper.text()).toContain('不能保存配置')
    expect(saveButton(wrapper)?.attributes('disabled')).toBeDefined()
    expect(
      buttonByText(wrapper, '从兼容配置导入')?.attributes('disabled'),
    ).toBeDefined()
  })

  it('imports legacy AppIDs through the dedicated endpoint', async () => {
    const { robotsApi, dashboardApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(robotResponseFixture())
    vi.mocked(dashboardApi.fetchConfig).mockResolvedValue(
      pluginConfigFixture({
        qq_platforms: [
          {
            appid: '987654321',
            platform: 'qq_official',
            secret_masked: 'ab***yz',
            secret_set: true,
          },
        ],
      }),
    )
    vi.mocked(robotsApi.importLegacyRobots).mockResolvedValue({
      ...robotResponseFixture(),
      version: 2,
    })

    const wrapper = await mount()
    await buttonByText(wrapper, '从兼容配置导入')?.trigger('click')
    await flush()
    expect(
      wrapper.find('[data-field="legacy-appids"] textarea').element,
    ).toHaveProperty('value', '987654321')
    await buttonByText(wrapper, '导入', true)?.trigger('click')
    await flush()

    expect(robotsApi.importLegacyRobots).toHaveBeenCalledWith(['987654321'], 1)
    expect(wrapper.text()).toContain('已从兼容配置导入机器人')
  })

  it('keeps unsaved drafts when importing legacy robots', async () => {
    const { robotsApi, dashboardApi, mount } = await loadView()
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(robotResponseFixture())
    vi.mocked(dashboardApi.fetchConfig).mockResolvedValue(
      pluginConfigFixture({
        qq_platforms: [
          {
            appid: '987654321',
            platform: 'qq_official',
            secret_masked: 'ab***yz',
            secret_set: true,
          },
        ],
      }),
    )
    vi.mocked(robotsApi.importLegacyRobots).mockResolvedValue({
      ...robotResponseFixture(),
      version: 2,
      robots: [
        ...robotResponseFixture().robots,
        robotFixture({
          id: 'robot-2',
          name: '导入机器人',
          appid: '987654321',
          secret_masked: 'cd***ef',
          scenes: {
            c2c: {
              enabled: true,
              items: [
                { type: 'send_message', name: '旧版菜单', message: '/legacy', parent: '' },
              ],
            },
          },
        }),
      ],
    })
    vi.mocked(robotsApi.saveRobots).mockResolvedValue({
      ...robotResponseFixture(),
      version: 3,
    })

    const wrapper = await mount()
    await buttonByText(wrapper, '新增机器人')?.trigger('click')
    await flush()
    await wrapper.find('[data-field="create-name"] input').setValue('草稿机器人')
    await wrapper.find('[data-field="create-appid"] input').setValue('111222333')
    await wrapper.find('[data-field="create-secret"] input').setValue('secret')
    await buttonByText(wrapper, '创建', true)?.trigger('click')
    await flush()

    await buttonByText(wrapper, '从兼容配置导入')?.trigger('click')
    await flush()
    await buttonByText(wrapper, '导入', true)?.trigger('click')
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
    vi.mocked(robotsApi.fetchRobots).mockResolvedValue(robotResponseFixture())

    const wrapper = await mount()
    await buttonByText(wrapper, '删除机器人配置')?.trigger('click')
    await flush()
    await buttonByText(wrapper, '确认删除', true)?.trigger('click')
    await flush()

    expect(wrapper.text()).toContain('还没有机器人')
    expect(wrapper.text()).toContain('保存后才会写入配置')
  })
})
