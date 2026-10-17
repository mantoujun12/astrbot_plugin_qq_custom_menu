import { describe, expect, it } from 'vitest'
import MenuEntryDialog from './MenuEntryDialog.vue'
import { flush, mountView } from '../../test/helpers'
import type { MenuEntry } from '../../types/dashboard'

const DIALOG_STUB = {
  VDialog: { template: '<div class="dialog-stub"><slot /></div>' },
}

function mountDialog(props: Record<string, unknown>) {
  return mountView(MenuEntryDialog, {
    props: {
      modelValue: true,
      entry: null,
      parent: '',
      menuNames: [],
      ...props,
    },
    global: { stubs: DIALOG_STUB },
  })
}

describe('MenuEntryDialog', () => {
  it('saves a send-message entry', async () => {
    const wrapper = mountDialog({})

    await wrapper.find('[data-field="menu-name"] input').setValue('帮助')
    await wrapper.find('[data-field="menu-message"] input').setValue('/help')
    await wrapper.find('[data-field="menu-save"]').trigger('click')

    expect(wrapper.emitted('save')?.[0]).toEqual([
      {
        type: 'send_message',
        name: '帮助',
        message: '/help',
        link: undefined,
        parent: '',
      },
    ])
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })

  it('requires a name and message', async () => {
    const wrapper = mountDialog({})

    await wrapper.find('[data-field="menu-save"]').trigger('click')
    expect(wrapper.text()).toContain('菜单名称不能为空')

    await wrapper.find('[data-field="menu-name"] input').setValue('帮助')
    await wrapper.find('[data-field="menu-save"]').trigger('click')
    expect(wrapper.text()).toContain('缺少消息内容')
    expect(wrapper.emitted('save')).toBeUndefined()
  })

  it('edits a link entry and normalizes its URL', async () => {
    const entry: MenuEntry = {
      type: 'link',
      name: '文档',
      link: 'docs.example.com',
      parent: '',
    }
    const wrapper = mountDialog({ entry })

    expect(wrapper.find('[data-field="menu-link"]').exists()).toBe(true)
    await wrapper.find('[data-field="menu-save"]').trigger('click')

    expect(wrapper.emitted('save')?.[0]?.[0]).toEqual({
      type: 'link',
      name: '文档',
      message: undefined,
      link: 'https://docs.example.com',
      parent: '',
    })
  })

  it('shows the sub-menu hint and locks the type when it has children', async () => {
    const entry: MenuEntry = { type: 'menu', name: '更多', parent: '' }
    const wrapper = mountDialog({ entry, hasChildren: true })

    expect(wrapper.text()).toContain('子菜单本身不发送内容')
    expect(wrapper.find('[data-field="menu-type"]').classes()).toContain(
      'v-input--disabled',
    )

    await wrapper.find('[data-field="menu-name"] input').setValue('更多')
    await wrapper.find('[data-field="menu-save"]').trigger('click')
    expect(wrapper.emitted('save')?.[0]?.[0]).toMatchObject({ type: 'menu', name: '更多' })
  })

  it('shows the parent label and rejects a missing link', async () => {
    const wrapper = mountDialog({
      entry: { type: 'link', name: '文档', link: '', parent: '更多' },
      parent: '更多',
      menuNames: ['更多'],
    })

    expect(wrapper.text()).toContain('父菜单：更多')
    await wrapper.find('[data-field="menu-save"]').trigger('click')
    expect(wrapper.text()).toContain('缺少链接')
  })

  it('closes on cancel', async () => {
    const wrapper = mountDialog({})

    const cancel = wrapper.findAll('button').find((button) => button.text() === '取消')
    await cancel?.trigger('click')
    await flush()

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([false])
  })
})
