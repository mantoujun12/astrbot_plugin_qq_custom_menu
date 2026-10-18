import { describe, expect, it } from 'vitest'
import { vi } from 'vitest'

async function makeRouter() {
  vi.resetModules()
  return (await import('./index')).router
}

describe('router', () => {
  it('redirects / to the status page', async () => {
    const router = await makeRouter()
    await router.push('/')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('status')
  })

  it.each(['/robots', '/compatibility', '/settings'])('resolves %s', async (path) => {
    const router = await makeRouter()
    await router.push(path)
    await router.isReady()

    expect(router.currentRoute.value.path).toBe(path)
  })

  it.each([
    ['/menu', 'compatibility'],
    ['/platforms', 'robots'],
  ])('keeps legacy route %s working', async (path, expected) => {
    const router = await makeRouter()
    await router.push(path)
    await router.isReady()

    expect(router.currentRoute.value.name).toBe(expected)
  })

  it('redirects unknown paths to status', async () => {
    const router = await makeRouter()
    await router.push('/missing')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('status')
  })
})
