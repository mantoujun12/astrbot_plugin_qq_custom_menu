import { describe, expect, it, vi } from 'vitest'
import { installBridge } from '../test/helpers'
import type { RobotConfigResponse } from '../types/robotConfig'

function responseFixture(): RobotConfigResponse {
  return {
    version: 2,
    robots: [],
    available_scenes: ['c2c'],
    menu_limits: { top_level_max: 10, sub_items_max: 5 },
  }
}

async function loadApi() {
  vi.resetModules()
  return import('./robots')
}

describe('robot config API', () => {
  it('falls back to mock data without a bridge', async () => {
    const api = await loadApi()

    const response = await api.fetchRobots()

    expect(response.robots[0].name).toBe('主机器人')
    expect(response.available_scenes).toEqual(['c2c'])
  })

  it('uses bridge endpoints for read, save and import', async () => {
    const bridge = installBridge({
      apiGet: vi.fn(async () => responseFixture()),
      apiPost: vi.fn(async (endpoint: string) => ({
        ...responseFixture(),
        endpoint,
      })),
    })
    const api = await loadApi()

    const fetched = await api.fetchRobots()
    const saved = await api.saveRobots({ version: 2, robots: [] })
    const imported = await api.importLegacyRobots(['app1'], 2)

    expect(fetched.version).toBe(2)
    expect(bridge.apiGet).toHaveBeenCalledWith('robots')
    expect(bridge.apiPost).toHaveBeenNthCalledWith(1, 'robots', {
      version: 2,
      robots: [],
    })
    expect(bridge.apiPost).toHaveBeenNthCalledWith(2, 'robots/import-legacy', {
      appids: ['app1'],
      version: 2,
    })
    expect(saved).toMatchObject({ endpoint: 'robots' })
    expect(imported).toMatchObject({ endpoint: 'robots/import-legacy' })
  })

  it('rejects writes without a backend', async () => {
    const api = await loadApi()

    await expect(api.saveRobots({ version: 1, robots: [] })).rejects.toThrow(
      'no backend',
    )
    await expect(api.importLegacyRobots(['app1'], 1)).rejects.toThrow(
      'no backend',
    )
  })
})
