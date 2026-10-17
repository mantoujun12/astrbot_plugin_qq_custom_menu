import { describe, expect, it } from 'vitest'
import MenuTree from './MenuTree.vue'
import { mountView } from '../../test/helpers'
import type { MenuEntry } from '../../types/dashboard'

const ENTRIES: MenuEntry[] = [
  { type: 'send_message', name: '帮助', message: '/help', parent: '' },
  { type: 'menu', name: '更多', parent: '' },
  { type: 'link', name: '文档', link: 'https://docs.example.com', parent: '更多' },
]

describe('MenuTree', () => {
  it('renders top-level entries and children with details', () => {
    const wrapper = mountView(MenuTree, { props: { entries: ENTRIES } })

    expect(wrapper.findAll('[data-field="menu-row"]')).toHaveLength(2)
    expect(wrapper.findAll('[data-field="menu-child-row"]')).toHaveLength(1)
    expect(wrapper.text()).toContain('帮助')
    expect(wrapper.text()).toContain('→ /help')
    expect(wrapper.text()).toContain('1 个子项')
    expect(wrapper.text()).toContain('https://docs.example.com')
  })

  it('emits add-child, edit and delete actions', async () => {
    const wrapper = mountView(MenuTree, { props: { entries: ENTRIES } })

    await wrapper.find('[aria-label="添加子项"]').trigger('click')
    expect(wrapper.emitted('addChild')?.[0]).toEqual(['更多'])

    const editButtons = wrapper.findAll('[aria-label="编辑"]')
    await editButtons[0].trigger('click')
    expect(wrapper.emitted('edit')?.[0]).toEqual([ENTRIES[0]])

    const deleteButtons = wrapper.findAll('[aria-label="删除"]')
    await deleteButtons[0].trigger('click')
    expect(wrapper.emitted('delete')?.[0]).toEqual([ENTRIES[0]])
  })

  it('hides actions in readonly mode', () => {
    const wrapper = mountView(MenuTree, {
      props: { entries: ENTRIES, readonly: true },
    })

    expect(wrapper.find('[aria-label="添加子项"]').exists()).toBe(false)
    expect(wrapper.find('[aria-label="编辑"]').exists()).toBe(false)
    expect(wrapper.find('[aria-label="删除"]').exists()).toBe(false)
  })

  it('shows the empty state', () => {
    const wrapper = mountView(MenuTree, { props: { entries: [] } })
    expect(wrapper.text()).toContain('还没有菜单条目')
  })
})
