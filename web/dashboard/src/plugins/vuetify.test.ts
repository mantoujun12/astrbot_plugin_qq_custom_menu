import { describe, expect, it } from 'vitest'
import { vuetify } from './vuetify'
import { THEME_DARK, THEME_LIGHT } from '../theme'

describe('vuetify', () => {
  it('registers both themes and the MDI icon set', () => {
    expect(vuetify.theme.themes.value[THEME_LIGHT]).toBeTruthy()
    expect(vuetify.theme.themes.value[THEME_DARK]).toBeTruthy()
    expect(vuetify.icons.defaultSet).toBe('mdi')
  })

  it('uses the host-compatible breakpoints', () => {
    expect(vuetify.display.thresholds.value.md).toBe(960)
    expect(vuetify.display.thresholds.value.lg).toBe(1280)
  })
})
