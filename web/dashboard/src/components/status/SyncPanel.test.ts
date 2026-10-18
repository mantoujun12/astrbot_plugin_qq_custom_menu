import { describe, expect, it, vi } from 'vitest'
import { flush, mountView } from '../../test/helpers'
import type { SyncRunState } from '../../types/dashboard'

const mocks = vi.hoisted(() => ({
  state: null as unknown,
  available: null as unknown,
  start: vi.fn(),
  attach: vi.fn(),
  retry: vi.fn(),
  stop: vi.fn(),
}))

vi.mock('../../composables/useSyncRun', async () => {
  const { computed, readonly, ref } = await import('vue')
  const state = ref<SyncRunState>({
    status: 'idle',
    platforms: 0,
    completed: 0,
    succeeded: 0,
    failed: 0,
    messages: [],
    platformStates: [],
    lastSeq: 0,
    error: '',
  })
  const available = ref(true)
  mocks.state = state
  mocks.available = available
  return {
    useSyncRun: () => ({
      state: readonly(state),
      available: computed(() => available.value),
      running: computed(() => state.value.status === 'running'),
      hasRun: computed(() => state.value.status !== 'idle'),
      start: mocks.start,
      attach: mocks.attach,
      retry: mocks.retry,
      stop: mocks.stop,
    }),
  }
})

import SyncPanel from './SyncPanel.vue'

function stateRef(): { value: SyncRunState } {
  return mocks.state as { value: SyncRunState }
}

function availableRef(): { value: boolean } {
  return mocks.available as { value: boolean }
}

function baseState(overrides: Partial<SyncRunState> = {}): SyncRunState {
  return {
    status: 'idle',
    platforms: 0,
    completed: 0,
    succeeded: 0,
    failed: 0,
    messages: [],
    platformStates: [],
    lastSeq: 0,
    error: '',
    ...overrides,
  }
}

describe('SyncPanel', () => {
  it('disables syncing without a backend', async () => {
    availableRef().value = false
    stateRef().value = baseState()
    const wrapper = mountView(SyncPanel)
    await flush()

    expect(wrapper.text()).toContain('本地开发环境没有 AstrBot 后端')
    const sync = wrapper.findAll('button').find((button) => button.text().includes('开始同步'))
    expect(sync?.attributes('disabled')).toBeDefined()
  })

  it('attaches on mount and starts a sync', async () => {
    availableRef().value = true
    stateRef().value = baseState()
    mocks.start.mockImplementationOnce(async (options: { onFinish?: () => void }) => {
      options.onFinish?.()
    })
    const wrapper = mountView(SyncPanel)
    await flush()

    expect(mocks.attach).toHaveBeenCalled()
    expect(wrapper.text()).toContain('还没有同步记录。')

    const sync = wrapper.findAll('button').find((button) => button.text().includes('开始同步'))
    await sync?.trigger('click')
    await flush()

    expect(mocks.start).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('finished')).toBeTruthy()
  })

  it('renders running progress, platform chips and logs', async () => {
    availableRef().value = true
    stateRef().value = baseState({
      status: 'running',
      platforms: 2,
      completed: 1,
      succeeded: 1,
      messages: ['reading'],
      platformStates: [
        { pf_id: 'a', index: 1, status: 'ok', saved: 1, error: '' },
      ],
    })
    const wrapper = mountView(SyncPanel)
    await flush()

    expect(wrapper.text()).toContain('正在同步')
    expect(wrapper.text()).toContain('1/2')
    expect(wrapper.text()).toContain('a')
    expect(wrapper.text()).toContain('reading')
  })

  it('renders the success summary', async () => {
    availableRef().value = true
    stateRef().value = baseState({
      status: 'done',
      platforms: 2,
      completed: 2,
      succeeded: 2,
    })
    const wrapper = mountView(SyncPanel)
    await flush()

    expect(wrapper.text()).toContain('同步完成：成功 2 个平台，失败 0 个')
  })

  it('shows a transport error and retries from the stored position', async () => {
    availableRef().value = true
    stateRef().value = baseState({
      status: 'failed',
      platforms: 1,
      error: 'stream failed',
      lastSeq: 4,
    })
    const wrapper = mountView(SyncPanel)
    await flush()

    expect(wrapper.text()).toContain('stream failed')
    const retry = wrapper.findAll('button').find((button) => button.text() === '重试')
    await retry?.trigger('click')

    expect(mocks.retry).toHaveBeenCalledTimes(1)
  })

  it('shows a warning summary when the run failed without a transport error', async () => {
    availableRef().value = true
    stateRef().value = baseState({
      status: 'failed',
      platforms: 1,
      succeeded: 0,
      failed: 1,
    })
    const wrapper = mountView(SyncPanel)
    await flush()

    expect(wrapper.text()).toContain('同步完成：成功 0 个平台，失败 1 个')
    expect(wrapper.findAll('button').some((button) => button.text() === '重试')).toBe(false)
  })

  it('stops the subscription on unmount', async () => {
    availableRef().value = true
    stateRef().value = baseState()
    const wrapper = mountView(SyncPanel)
    await flush()

    wrapper.unmount()

    expect(mocks.stop).toHaveBeenCalled()
  })
})
