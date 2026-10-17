import { describe, expect, it } from 'vitest'
import { getBridge, waitForBridge } from './bridge'
import { createBridgeStub } from './test/helpers'

describe('getBridge', () => {
  it('returns null when the host has not injected the SDK', () => {
    expect(getBridge()).toBeNull()
  })

  it('reads AstrBotPluginView first and falls back to AstrBotPluginPage', () => {
    const main = createBridgeStub()
    window.AstrBotPluginView = main
    expect(getBridge()).toBe(main)

    delete window.AstrBotPluginView
    const legacy = createBridgeStub()
    window.AstrBotPluginPage = legacy
    expect(getBridge()).toBe(legacy)
  })
})

describe('waitForBridge', () => {
  it('resolves immediately when the bridge already exists', async () => {
    const bridge = createBridgeStub()
    window.AstrBotPluginView = bridge

    await expect(waitForBridge(10)).resolves.toBe(bridge)
  })

  it('polls until the bridge is injected', async () => {
    const bridge = createBridgeStub()
    setTimeout(() => {
      window.AstrBotPluginView = bridge
    }, 20)

    await expect(waitForBridge(500, 5)).resolves.toBe(bridge)
  })

  it('resolves null after the timeout', async () => {
    await expect(waitForBridge(20, 5)).resolves.toBeNull()
  })
})
