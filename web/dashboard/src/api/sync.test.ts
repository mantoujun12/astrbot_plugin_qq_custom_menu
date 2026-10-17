import { describe, expect, it, vi } from 'vitest'
import {
  initialSyncState,
  isSyncEvent,
  reduceSyncEvent,
  startSync,
  subscribeSyncRun,
} from './sync'
import type { PluginViewSSEHandlers } from '../bridge'
import { installBridge } from '../test/helpers'

describe('sync api', () => {
  it('starts from an empty state', () => {
    expect(initialSyncState()).toEqual({
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
  })

  it('validates event shapes', () => {
    expect(isSyncEvent(null)).toBe(false)
    expect(isSyncEvent('x')).toBe(false)
    expect(isSyncEvent({ type: 'unknown' })).toBe(false)
    expect(isSyncEvent({ type: 'message', seq: 1, text: 'x' })).toBe(true)
    expect(isSyncEvent({ type: 'finish', seq: 1 })).toBe(true)
  })

  it('reduces start, message, platform and finish events', () => {
    let state = initialSyncState()

    state = reduceSyncEvent(state, {
      type: 'start',
      seq: 1,
      mode: 'sync',
      platforms: 2,
      items: 3,
    })
    expect(state.status).toBe('running')
    expect(state.platforms).toBe(2)

    state = reduceSyncEvent(state, { type: 'message', seq: 2, text: 'hello' })
    expect(state.messages).toEqual(['hello'])

    state = reduceSyncEvent(state, {
      type: 'platform',
      seq: 3,
      pf_id: 'b',
      index: 2,
      total: 2,
      status: 'ok',
      saved: 3,
    })
    state = reduceSyncEvent(state, {
      type: 'platform',
      seq: 4,
      pf_id: 'a',
      index: 1,
      total: 2,
      status: 'error',
      error: 'boom',
    })
    expect(state.platformStates.map((item) => item.pf_id)).toEqual(['a', 'b'])
    expect(state.completed).toBe(2)
    expect(state.succeeded).toBe(1)
    expect(state.failed).toBe(1)

    state = reduceSyncEvent(state, {
      type: 'finish',
      seq: 5,
      ok: true,
      platforms: 2,
      succeeded: 1,
      failed: 1,
    })
    expect(state.status).toBe('done')
    expect(state.lastSeq).toBe(5)
  })

  it('marks a failing finish and keeps an existing platform count', () => {
    const state = reduceSyncEvent(
      { ...initialSyncState(), platforms: 3 },
      {
        type: 'finish',
        seq: 2,
        ok: false,
        platforms: 0,
        succeeded: 0,
        failed: 3,
        error: 'failed',
      },
    )
    expect(state.status).toBe('failed')
    expect(state.platforms).toBe(3)
    expect(state.error).toBe('failed')
  })

  it('requires a backend for starting and subscribing', async () => {
    await expect(startSync()).rejects.toThrow('no backend')
    await expect(
      subscribeSyncRun({ onEvent: () => undefined }),
    ).rejects.toThrow('no backend')
  })

  it('starts a sync through the bridge', async () => {
    const bridge = installBridge({ apiPost: vi.fn(async () => ({ started: true, busy: false })) })

    await expect(startSync()).resolves.toEqual({ started: true, busy: false })
    expect(bridge.apiPost).toHaveBeenCalledWith('sync')
  })

  it('subscribes, forwards valid events and stops the stream', async () => {
    let handlers: PluginViewSSEHandlers = {}
    const bridge = installBridge({
      subscribeSSE: vi.fn(async (_endpoint, next) => {
        handlers = next ?? {}
        return 'sub-42'
      }),
    })
    const events: unknown[] = []
    const onOpen = vi.fn()
    const onError = vi.fn()

    const subscription = await subscribeSyncRun({
      since: 3,
      onEvent: (event) => events.push(event),
      onOpen,
      onError,
    })

    expect(bridge.subscribeSSE).toHaveBeenCalledWith(
      'sync/events',
      expect.any(Object),
      { since: 3 },
    )

    handlers.onOpen?.()
    handlers.onMessage?.({
      raw: '{"type":"message","seq":4,"text":"x"}',
      parsed: { type: 'message', seq: 4, text: 'x' },
      eventType: 'message',
    })
    handlers.onMessage?.({
      raw: 'not json',
      parsed: 'not json',
      eventType: 'message',
    })
    handlers.onError?.()

    expect(onOpen).toHaveBeenCalledTimes(1)
    expect(events).toEqual([{ type: 'message', seq: 4, text: 'x' }])
    expect(onError).toHaveBeenCalledTimes(1)

    await subscription.stop()
    expect(bridge.unsubscribeSSE).toHaveBeenCalledWith('sub-42')
  })
})
