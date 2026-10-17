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

  it.each(['/menu', '/platforms', '/settings'])('resolves %s', async (path) => {
    const router = await makeRouter()
    await router.push(path)
    await router.isReady()

    expect(router.currentRoute.value.path).toBe(path)
  })

  it('redirects unknown paths to status', async () => {
    const router = await makeRouter()
    await router.push('/missing')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('status')
  })
})
