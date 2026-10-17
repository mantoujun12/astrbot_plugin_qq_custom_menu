import { describe, expect, it, vi } from 'vitest'
import { fetchConfig, fetchStatus, saveConfig } from './dashboard'
import { MOCK_CONFIG, MOCK_STATUS } from './mock'
import { installBridge } from '../test/helpers'

describe('dashboard api', () => {
  it('returns mock data without a bridge', async () => {
    await expect(fetchStatus()).resolves.toBe(MOCK_STATUS)
    await expect(fetchStatus({ refresh: true })).resolves.toBe(MOCK_STATUS)
    await expect(fetchConfig()).resolves.toBe(MOCK_CONFIG)
  })

  it('refuses to fake a successful save without a bridge', async () => {
    await expect(saveConfig({ language: 'en-US' })).rejects.toThrow('no backend')
  })

  it('calls the status endpoint and forwards refresh', async () => {
    const response = { ...MOCK_STATUS }
    const bridge = installBridge({ apiGet: vi.fn(async () => response) })

    await expect(fetchStatus()).resolves.toBe(response)
    expect(bridge.apiGet).toHaveBeenCalledWith('status', undefined)

    await fetchStatus({ refresh: true })
    expect(bridge.apiGet).toHaveBeenLastCalledWith('status', { refresh: 1 })
  })

  it('reads and writes config through the bridge', async () => {
    const response = { ...MOCK_CONFIG }
    const bridge = installBridge({
      apiGet: vi.fn(async () => response),
      apiPost: vi.fn(async () => response),
    })

    await expect(fetchConfig()).resolves.toBe(response)
    expect(bridge.apiGet).toHaveBeenCalledWith('config')

    await expect(saveConfig({ language: 'en-US' })).resolves.toBe(response)
    expect(bridge.apiPost).toHaveBeenCalledWith('config', { language: 'en-US' })
  })

  it('passes reactive payloads as plain objects', async () => {
    const bridge = installBridge({ apiPost: vi.fn(async () => MOCK_CONFIG) })

    await saveConfig({ menu: [{ type: 'menu', name: 'x', parent: '' }] })

    const payload = (bridge.apiPost as ReturnType<typeof vi.fn>).mock.calls[0][1]
    expect(payload).toEqual({ menu: [{ type: 'menu', name: 'x', parent: '' }] })
  })
})
