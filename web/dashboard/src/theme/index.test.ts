import { describe, expect, it } from 'vitest'
import { THEME_DARK, THEME_LIGHT, darkTheme, lightTheme } from './index'

describe('theme', () => {
  it('exposes distinct light and dark theme names', () => {
    expect(THEME_LIGHT).not.toBe(THEME_DARK)
    expect(lightTheme.dark).toBe(false)
    expect(darkTheme.dark).toBe(true)
  })

  it('carries the shared brand colors', () => {
    expect(lightTheme.colors?.primary).toBe('#3c96ca')
    expect(darkTheme.colors?.primary).toBe('#5ba4d4')
    expect(lightTheme.colors?.background).toBe('#ffffff')
    expect(darkTheme.colors?.background).toBe('#1a1a1a')
  })
})
