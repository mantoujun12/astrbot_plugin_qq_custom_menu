/**
 * 组件测试的公共工具。
 *
 * 挂载统一走 @vue/test-utils 的 mount，并带上真实的 Vuetify 实例，这样主题名、
 * 图标集与断点和运行时一致。断言只基于文本、自有 class、属性与 emit，
 * 不断言 Vuetify 的内部结构。
 */

import { mount, type MountingOptions, type Stubs, type VueWrapper } from '@vue/test-utils'
import { nextTick, type Component } from 'vue'
import { createMemoryHistory, createRouter, type RouteRecordRaw, type Router } from 'vue-router'
import { vi } from 'vitest'
import { vuetify } from '../plugins/vuetify'
import type { PluginViewBridge } from '../bridge'

/** 等 Vue 完成一轮渲染，并让同一 tick 里的 promise 链落地 */
export async function flush(): Promise<void> {
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

/** 创建并导航到一个内存路由，省去每个视图测试重复的 push + isReady */
export async function makeRouter(routes: RouteRecordRaw[], initial = '/'): Promise<Router> {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(initial)
  await router.isReady()
  return router
}

/** 按可见文本查找按钮；exact=false 时按包含匹配 */
export function buttonByText(
  wrapper: VueWrapper,
  text: string,
  exact = false,
) {
  return wrapper
    .findAll('button')
    .find((button) => (exact ? button.text().trim() === text : button.text().includes(text)))
}

/** 视图通用的「保存」按钮 */
export function saveButton(wrapper: VueWrapper) {
  return buttonByText(wrapper, '保存', true)
}

interface DashboardViewOptions<T> {
  /** 动态导入被测视图使用的 API 模块 */
  api: () => Promise<T>
  /** 动态导入被测视图，例如 () => import('./MenuView.vue') */
  component: () => Promise<{ default: Component }>
  /** false 表示不注入 bridge（模拟本地 mock 模式） */
  bridge?: Partial<PluginViewBridge> | false
  routes?: RouteRecordRaw[]
  initial?: string
  stubs?: Stubs
  /** 返回「首屏数据已到位」的谓词，交给 waitUntil 轮询 */
  waitFor: (api: T) => () => boolean
}

/**
 * 视图测试的通用装配：安装 bridge、重置模块、导入 API/组件、建路由并挂载。
 *
 * 视图测试几乎都要经历同一套 bootstrap，集中后每个文件只需声明差异部分。
 */
export async function loadDashboardView<T>(options: DashboardViewOptions<T>) {
  const bridge =
    options.bridge === false ? null : installBridge(options.bridge ?? {})
  vi.resetModules()
  const api = await options.api()
  const { default: component } = await options.component()
  const router = options.routes
    ? await makeRouter(options.routes, options.initial)
    : undefined

  return {
    bridge,
    api,
    router,
    async mount() {
      const wrapper = mountView(component, {
        global: {
          ...(router ? { plugins: [router] } : {}),
          ...(options.stubs ? { stubs: options.stubs } : {}),
        },
      })
      await waitUntil(options.waitFor(api))
      await flush()
      return wrapper
    },
  }
}

/** 挂载一个视图/组件，默认装上真实 Vuetify；需要路由的用例自己传 router */
export function mountView(
  component: Component,
  options: MountingOptions<Record<string, unknown>> = {},
): VueWrapper {
  const globalOptions = options.global ?? {}
  return mount(component, {
    ...options,
    global: {
      ...globalOptions,
      plugins: [vuetify, ...(globalOptions.plugins ?? [])],
    },
  })
}

/**
 * 供测试注入的最小 bridge，覆盖视图真正用到的方法。
 *
 * t() 默认回 fallback，与本地 `pnpm dev` 的行为一致；要断言「确实走了宿主
 * 翻译」时用 overrides 覆盖 t。
 */
export function createBridgeStub(
  overrides: Partial<PluginViewBridge> = {},
): PluginViewBridge {
  return {
    ready: vi.fn(async () => ({})),
    getContext: vi.fn(() => null),
    getLocale: vi.fn(() => 'zh-CN'),
    t: vi.fn((key: string, fallback?: string) => fallback ?? key),
    onContext: vi.fn(() => () => {}),
    apiGet: vi.fn(async () => null),
    apiPost: vi.fn(async () => null),
    subscribeSSE: vi.fn(async () => 'sub-1'),
    unsubscribeSSE: vi.fn(async () => ({ subscriptionId: 'sub-1' })),
    ...overrides,
  }
}

/** 注入 bridge 替身并返回它 */
export function installBridge(
  overrides: Partial<PluginViewBridge> = {},
): PluginViewBridge {
  const bridge = createBridgeStub(overrides)
  window.AstrBotPluginView = bridge
  return bridge
}

/**
 * 轮询等待某个条件成立，再放行一轮渲染。
 *
 * useBridge 的首轮 bootstrap 在 dev 下要等 300ms，固定 sleep 在慢机器上会飘，
 * 所以统一用条件等待：既快又不 flaky。
 */
export async function waitUntil(
  predicate: () => boolean,
  timeoutMs = 2000,
): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (!predicate()) {
    if (Date.now() > deadline) {
      throw new Error('waitUntil timed out')
    }
    await new Promise((resolve) => setTimeout(resolve, 20))
  }
  await flush()
}
