import { describe, expect, it } from 'vitest'
import { mdiServerOutline } from '@mdi/js'
import StatCard from './StatCard.vue'
import { mountView } from '../../test/helpers'

describe('StatCard', () => {
  it('renders the label, value and watermark icon', () => {
    const wrapper = mountView(StatCard, {
      props: { title: 'QQ 平台', value: 3, icon: mdiServerOutline },
    })

    expect(wrapper.text()).toContain('QQ 平台')
    expect(wrapper.find('.qc-metric-value').text()).toBe('3')
    expect(wrapper.find('.qc-stat-watermark').exists()).toBe(true)
  })

  it('highlights the value when it reaches the limit', () => {
    const wrapper = mountView(StatCard, {
      props: { title: '一级菜单', value: 10, max: 10, emphasizeAtLimit: true },
    })

    expect(wrapper.find('.qc-metric-value').classes()).toContain('text-error')
  })

  it('does not highlight below the limit or without the flag', () => {
    const below = mountView(StatCard, {
      props: { title: '一级菜单', value: 9, max: 10, emphasizeAtLimit: true },
    })
    expect(below.find('.qc-metric-value').classes()).not.toContain('text-error')

    const unflagged = mountView(StatCard, {
      props: { title: '一级菜单', value: 10, max: 10 },
    })
    expect(unflagged.find('.qc-metric-value').classes()).not.toContain('text-error')
  })
})
