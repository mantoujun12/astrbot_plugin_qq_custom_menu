import { describe, expect, it } from 'vitest'
import { mountView } from '../../test/helpers'
import ThemeColorField from './ThemeColorField.vue'

type FieldProps = {
  modelValue: string
  label: string
  hint: string
  invalidMessage: string
  disabled?: boolean
}

function mountField(props: Partial<FieldProps> = {}) {
  return mountView(ThemeColorField, {
    props: {
      modelValue: '#3c96ca',
      label: '主色',
      hint: '使用 #RRGGBB 格式。',
      invalidMessage: '请输入 #RRGGBB 格式的颜色。',
      ...props,
    },
  })
}

describe('ThemeColorField', () => {
  it('emits text input changes and exposes a color trigger', async () => {
    const wrapper = mountField()
    const input = wrapper.find('input')

    await input.setValue('#AABBCC')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['#AABBCC'])
    expect(wrapper.find('.qc-color-trigger').attributes('style')).toContain(
      '#3c96ca',
    )
  })

  it('shows the invalid color message and disables the trigger', async () => {
    const wrapper = mountField({ modelValue: 'red', disabled: true })
    const rules = wrapper.findComponent({ name: 'VTextField' }).props('rules') as Array<
      (value: string) => true | string
    >

    expect(rules[0]('red')).toBe('请输入 #RRGGBB 格式的颜色。')
    expect(rules[0]('#aabbcc')).toBe(true)
    expect(wrapper.find('.qc-color-trigger').attributes('disabled')).toBeDefined()
  })
})
