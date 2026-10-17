import { describe, expect, it, vi } from 'vitest'
import { installBridge, waitUntil } from '../test/helpers'

async function loadUseBridge() {
  vi.resetModules()
  return import('./useBridge')
}

describe('useBridge', () => {
  it('falls back to defaults when no bridge is injected', async () => {
    const { useBridge } = await loadUseBridge()
    const { ready, hasBackend, t, locale, isDark } = useBridge()

    await waitUntil(() => ready.value)

    expect(hasBackend.value).toBe(false)
    expect(t('missing.key', 'fallback')).toBe('fallback')
    expect(t('missing.key')).toBe('missing.key')
    expect(locale.value).toBe('zh-CN')
    expect(typeof isDark.value).toBe('boolean')
  })

  it('reads the initial dark theme from the host html attribute', async () => {
    document.documentElement.dataset.theme = 'dark'
    const { useBridge } = await loadUseBridge()
    const { ready, isDark } = useBridge()

    await waitUntil(() => ready.value)

    expect(isDark.value).toBe(true)
  })

  it('attaches to the bridge and applies the host context', async () => {
    const bridge = installBridge({
      t: vi.fn((_key: string, fallback?: string) => `host:${fallback ?? ''}`),
      getContext: vi.fn(() => ({
        locale: 'en-US',
        isDark: true,
        pageTitle: 'Host title',
      })),
      ready: vi.fn(async () => ({ locale: 'en-US' })),
    })
    const { useBridge } = await loadUseBridge()
    const { ready, hasBackend, t, locale, isDark, context } = useBridge()

    await waitUntil(() => ready.value)

    expect(hasBackend.value).toBe(true)
    expect(t('x', 'fallback')).toBe('host:fallback')
    expect(locale.value).toBe('en-US')
    expect(isDark.value).toBe(true)
    expect(context.value?.pageTitle).toBe('Host title')
    expect(bridge.ready).toHaveBeenCalledTimes(1)
  })

  it('reacts to host context changes', async () => {
    let handler: () => void = () => {}
    let dark = false
    installBridge({
      getContext: vi.fn(() => ({ isDark: dark, locale: dark ? 'en-US' : 'zh-CN' })),
      onContext: vi.fn((next: () => void) => {
        handler = next
        return () => {}
      }),
    })
    const { useBridge } = await loadUseBridge()
    const { ready, isDark, locale } = useBridge()

    await waitUntil(() => ready.value)
    expect(isDark.value).toBe(false)

    dark = true
    handler()

    expect(isDark.value).toBe(true)
    expect(locale.value).toBe('en-US')
  })

  it('keeps rendering when ready() rejects', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    installBridge({
      ready: vi.fn(async () => {
        throw new Error('ready failed')
      }),
      getContext: vi.fn(() => ({ isDark: true })),
    })
    const { useBridge } = await loadUseBridge()
    const { ready, hasBackend, isDark } = useBridge()

    await waitUntil(() => ready.value)

    expect(hasBackend.value).toBe(true)
    expect(isDark.value).toBe(true)
    expect(warn).toHaveBeenCalled()
  })
})
