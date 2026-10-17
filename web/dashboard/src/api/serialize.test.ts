import { describe, expect, it } from 'vitest'
import { reactive } from 'vue'
import { toPlain } from './serialize'

describe('toPlain', () => {
  it('returns primitives and nullish values unchanged', () => {
    expect(toPlain(null)).toBeNull()
    expect(toPlain(undefined)).toBeUndefined()
    expect(toPlain('x')).toBe('x')
    expect(toPlain(3)).toBe(3)
  })

  it('strips Vue proxies so postMessage can clone the payload', () => {
    const source = reactive({ name: 'x', nested: { value: 1 } })
    const plain = toPlain(source)

    expect(plain).toEqual({ name: 'x', nested: { value: 1 } })
    // 纯对象不能再带响应式标记
    expect(JSON.stringify(plain)).toBe('{"name":"x","nested":{"value":1}}')
  })

  it('drops undefined fields like JSON serialization does', () => {
    const plain = toPlain({ a: 1, b: undefined, c: null })
    expect(plain).toEqual({ a: 1, c: null })
  })
})
