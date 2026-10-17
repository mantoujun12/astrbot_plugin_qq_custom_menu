import { describe, expect, it } from 'vitest'
import {
  buildPlatformPayload,
  newPlatform,
  toPlatformForm,
  validatePlatforms,
} from './platformForm'

const t = (_key: string, fallback?: string): string => fallback ?? _key

describe('platformForm helpers', () => {
  it('converts saved platforms into editable rows', () => {
    expect(
      toPlatformForm([
        {
          appid: '123',
          platform: 'qq_official_webhook',
          secret_masked: 'ab***yz',
          secret_set: true,
        },
        {
          appid: '456',
          platform: 'weird',
          secret_masked: '',
          secret_set: false,
        },
      ]),
    ).toEqual([
      {
        appid: '123',
        secret: '',
        platform: 'qq_official_webhook',
        secret_masked: 'ab***yz',
        secret_set: true,
        isNew: false,
      },
      {
        appid: '456',
        secret: '',
        platform: 'qq_official',
        secret_masked: '',
        secret_set: false,
        isNew: false,
      },
    ])
  })

  it('creates a blank row', () => {
    expect(newPlatform()).toEqual({
      appid: '',
      secret: '',
      platform: 'qq_official',
      secret_masked: '',
      secret_set: false,
      isNew: true,
    })
  })

  it('accepts saved rows whose secret is left empty', () => {
    const rows = [
      {
        appid: '123',
        secret: '',
        platform: 'qq_official' as const,
        secret_masked: 'ab***yz',
        secret_set: true,
        isNew: false,
      },
    ]
    expect(validatePlatforms(rows, t)).toEqual({ ok: true, reason: '' })
  })

  it('rejects invalid rows', () => {
    const base = newPlatform()
    const cases = [
      [{ ...base, appid: ' ' }],
      [
        { ...base, appid: '1', secret: 's' },
        { ...base, appid: '1', secret: 's' },
      ],
      [{ ...base, appid: '1', secret: 's', platform: 'bad' }],
      [{ ...base, appid: '1', secret: '' }],
    ]

    for (const rows of cases) {
      const result = validatePlatforms(rows as never, t)
      expect(result.ok, JSON.stringify(rows)).toBe(false)
      expect(result.reason).not.toBe('')
    }
  })

  it('builds a trimmed payload', () => {
    const rows = [
      {
        appid: ' 123 ',
        secret: ' secret ',
        platform: 'qq_official' as const,
        secret_masked: '',
        secret_set: false,
        isNew: true,
      },
    ]
    expect(buildPlatformPayload(rows)).toEqual([
      { appid: '123', secret: 'secret', platform: 'qq_official' },
    ])
  })
})
