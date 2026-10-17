import { beforeEach, describe, expect, it, vi } from 'vitest'
import { installBridge, waitUntil } from '../test/helpers'
import type { SyncEvent } from '../types/dashboard'

const mocks = vi.hoisted(() => ({
  startSync: vi.fn(async () => ({ started: true, busy: false })),
  subscribeSyncRun: vi.fn(),
}))

vi.mock('../api/sync', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/sync')>()
  return {
    ...actual,
    startSync: mocks.startSync,
    subscribeSyncRun: mocks.subscribeSyncRun,
  }
})

interface CapturedOptions {
  since?: number
  onEvent(event: SyncEvent): void
  onError?(error: Error): void
}

let captured: CapturedOptions | null = null
let stop: ReturnType<typeof vi.fn>

async function loadUseSyncRun() {
  vi.resetModules()
  return (await import('./useSyncRun')).useSyncRun()
}

beforeEach(() => {
  captured = null
  stop = vi.fn(async () => undefined)
  mocks.startSync.mockClear()
  mocks.subscribeSyncRun.mockReset()
  mocks.subscribeSyncRun.mockImplementation(
    async (options: CapturedOptions) => {
      captured = options
      return { stop }
    },
  )
})

describe('useSyncRun', () => {
  it('is unavailable without a backend', async () => {
    const run = await loadUseSyncRun()
    await waitUntil(() => run.available.value === false)

    await expect(run.start()).rejects.toThrow('no backend')
    run.attach()
    run.retry()

    expect(mocks.startSync).not.toHaveBeenCalled()
    expect(mocks.subscribeSyncRun).not.toHaveBeenCalled()
  })

  it('starts a run, reduces events and stops on finish', async () => {
    installBridge()
    const run = await loadUseSyncRun()
    await waitUntil(() => run.available.value)

    const onFinish = vi.fn()
    await run.start({ onFinish })
    await waitUntil(() => mocks.subscribeSyncRun.mock.calls.length === 1)

    expect(mocks.startSync).toHaveBeenCalledTimes(1)
    expect(captured?.since).toBe(0)

    captured?.onEvent({ type: 'start', seq: 1, mode: 'sync', platforms: 1, items: 2 })
    captured?.onEvent({ type: 'message', seq: 2, text: 'reading' })
    captured?.onEvent({
      type: 'platform',
      seq: 3,
      pf_id: 'a',
      index: 1,
      total: 1,
      status: 'ok',
      saved: 2,
    })
    captured?.onEvent({
      type: 'finish',
      seq: 4,
      ok: true,
      platforms: 1,
      succeeded: 1,
      failed: 0,
    })

    expect(run.state.value.status).toBe('done')
    expect(run.state.value.succeeded).toBe(1)
    expect(run.state.value.messages).toEqual(['reading'])
    expect(onFinish).toHaveBeenCalledTimes(1)
    expect(stop).toHaveBeenCalled()
  })

  it('attaches to an existing run and reports stream errors', async () => {
    installBridge()
    const run = await loadUseSyncRun()
    await waitUntil(() => run.available.value)

    const onFinish = vi.fn()
    run.attach(onFinish)
    await waitUntil(() => captured !== null)

    captured?.onError?.(new Error('stream failed'))
    expect(run.state.value.status).toBe('failed')
    expect(run.state.value.error).toBe('stream failed')
  })

  it('retries from the last received seq', async () => {
    installBridge()
    const run = await loadUseSyncRun()
    await waitUntil(() => run.available.value)

    await run.start()
    await waitUntil(() => captured !== null)
    captured?.onEvent({ type: 'message', seq: 7, text: 'x' })

    run.retry()
    await waitUntil(() => mocks.subscribeSyncRun.mock.calls.length === 2)

    expect(captured?.since).toBe(7)
  })

  it('turns a rejected subscription into a failed state', async () => {
    installBridge()
    mocks.subscribeSyncRun.mockRejectedValueOnce(new Error('cannot subscribe'))
    const run = await loadUseSyncRun()
    await waitUntil(() => run.available.value)

    await run.start()

    expect(run.state.value.status).toBe('failed')
    expect(run.state.value.error).toBe('cannot subscribe')
  })
})
