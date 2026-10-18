import { describe, expect, it } from 'vitest'
import type { useTheme } from 'vuetify'
import {
  DEFAULT_THEME_COLORS,
  THEME_DARK,
  THEME_LIGHT,
  applyThemeColors,
  darkTheme,
  isHexColor,
  lightTheme,
  resolveThemeColors,
} from './index'

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

  it('normalizes configured colors and falls back for invalid values', () => {
    expect(
      resolveThemeColors({
        primary_color: ' #AABBCC ',
        secondary_color: '#112233',
      }),
    ).toEqual({
      primary: '#aabbcc',
      secondary: '#112233',
    })
    expect(isHexColor('#AABBCC')).toBe(true)
    expect(isHexColor('#abc')).toBe(false)
    expect(resolveThemeColors({ primary_color: 'red' })).toEqual(
      DEFAULT_THEME_COLORS,
    )
  })

  it('applies colors to both registered themes', () => {
    const themes = {
      [THEME_LIGHT]: { colors: {} },
      [THEME_DARK]: { colors: {} },
    }
    const theme = {
      themes: { value: themes },
    } as unknown as ReturnType<typeof useTheme>

    applyThemeColors(theme, { primary: '#123456', secondary: '#654321' })

    expect(themes[THEME_LIGHT].colors).toEqual({
      primary: '#123456',
      secondary: '#654321',
    })
    expect(themes[THEME_DARK].colors).toEqual({
      primary: '#123456',
      secondary: '#654321',
    })
  })
})
