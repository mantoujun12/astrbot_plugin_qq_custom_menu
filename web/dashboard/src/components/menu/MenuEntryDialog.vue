<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { mdiAlertCircleOutline } from '@mdi/js'
import { useBridge } from '../../composables/useBridge'
import { normalizeLink } from '../../views/menuForm'
import type { MenuEntry, MenuType } from '../../types/dashboard'

const props = defineProps<{
  modelValue: boolean
  entry: MenuEntry | null
  /** 新增子项时固定所属母菜单；编辑已有条目时沿用条目的 parent */
  parent: string
  menuNames: string[]
  /** 母菜单已有子项时禁止改成其它类型，避免子项失去父级 */
  hasChildren?: boolean
}>()

defineOptions({ name: 'MenuEntryDialog' })

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: [entry: MenuEntry]
}>()

const { t } = useBridge()

const type = ref<MenuType>('send_message')
const name = ref('')
const message = ref('')
const link = ref('')
const switchId = ref('')
const switchDefault = ref(false)
const error = ref('')

const isEditing = computed(() => props.entry !== null)
const effectiveParent = computed(() => props.entry?.parent ?? props.parent)
const menuLocked = computed(
  () => props.entry?.type === 'menu' && props.hasChildren === true,
)

const typeOptions = computed(() => {
  const types: MenuType[] = effectiveParent.value
    ? ['send_message', 'link']
    : ['send_message', 'link', 'switch', 'menu']
  return types.map((value) => ({
    title: t(`pages.dashboard.menu.type.${value}`, TYPE_FALLBACK[value]),
    value,
  }))
})

const TYPE_FALLBACK: Record<MenuType, string> = {
  send_message: '发送消息',
  link: '跳转链接',
  switch: '开关',
  menu: '子菜单',
}

function reset(): void {
  const source = props.entry
  type.value = source?.type ?? 'send_message'
  name.value = source?.name ?? ''
  message.value = source?.message ?? ''
  link.value = source?.link ?? ''
  switchId.value = source?.switch_id ?? ''
  switchDefault.value = source?.default ?? false
  error.value = ''
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      reset()
    }
  },
  { immediate: true },
)

watch(
  () => props.entry,
  () => {
    if (props.modelValue) {
      reset()
    }
  },
)

function close(): void {
  emit('update:modelValue', false)
}

function onSave(): void {
  const trimmedName = name.value.trim()
  if (!trimmedName) {
    error.value = t('pages.dashboard.menu.validation.nameEmpty', '菜单名称不能为空')
    return
  }
  if (type.value === 'menu' && effectiveParent.value) {
    error.value = t('pages.dashboard.menu.validation.menuParent', '子菜单不能设置父菜单')
    return
  }
  if (type.value === 'send_message' && !message.value.trim()) {
    error.value = t(
      'pages.dashboard.menu.validation.messageEmpty',
      '菜单「{name}」缺少消息内容',
    ).replace('{name}', trimmedName)
    return
  }
  if (type.value === 'link' && !link.value.trim()) {
    error.value = t(
      'pages.dashboard.menu.validation.linkEmpty',
      '菜单「{name}」缺少链接',
    ).replace('{name}', trimmedName)
    return
  }
  if (type.value === 'switch' && !switchId.value.trim()) {
    error.value = t(
      'pages.dashboard.menu.validation.switchIdEmpty',
      '菜单「{name}」缺少开关 ID',
    ).replace('{name}', trimmedName)
    return
  }

  emit('save', {
    type: type.value,
    name: trimmedName,
    message: type.value === 'send_message' ? message.value.trim() : undefined,
    link: type.value === 'link' ? normalizeLink(link.value) : undefined,
    switch_id: type.value === 'switch' ? switchId.value.trim() : undefined,
    default: type.value === 'switch' ? switchDefault.value : undefined,
    parent: effectiveParent.value,
  })
  close()
}
</script>

<template>
  <v-dialog
    :model-value="modelValue"
    max-width="540"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card class="qc-card">
      <v-card-item class="px-5 pt-5">
        <v-card-title class="text-body-large">
          {{
            isEditing
              ? t('pages.dashboard.menu.dialogEdit', '编辑菜单条目')
              : t('pages.dashboard.menu.dialogAdd', '添加菜单条目')
          }}
        </v-card-title>
        <v-card-subtitle v-if="effectiveParent">
          {{
            t('pages.dashboard.menu.parentLabel', '父菜单：{parent}').replace(
              '{parent}',
              effectiveParent,
            )
          }}
        </v-card-subtitle>
      </v-card-item>

      <v-card-text class="px-5 pb-3 pt-3">
        <v-select
          v-model="type"
          data-field="menu-type"
          :items="typeOptions"
          :label="t('pages.dashboard.menu.fieldType', '类型')"
          :disabled="menuLocked"
          variant="outlined"
          density="compact"
          class="mb-3"
          hide-details
        />
        <v-text-field
          v-model="name"
          data-field="menu-name"
          :label="t('pages.dashboard.menu.fieldName', '菜单名称')"
          variant="outlined"
          density="compact"
          class="mb-3"
          hide-details
        />

        <v-text-field
          v-if="type === 'send_message'"
          v-model="message"
          data-field="menu-message"
          :label="t('pages.dashboard.menu.fieldMessage', '点击后发送的消息')"
          :hint="t('pages.dashboard.menu.messageHint', '例如 /help')"
          variant="outlined"
          density="compact"
          persistent-hint
          class="mb-3"
        />
        <v-text-field
          v-else-if="type === 'link'"
          v-model="link"
          data-field="menu-link"
          :label="t('pages.dashboard.menu.fieldLink', '点击后打开的链接')"
          :hint="
            t(
              'pages.dashboard.menu.linkHint',
              'QQ 要求 https://；未填写协议时会自动补全。',
            )
          "
          variant="outlined"
          density="compact"
          persistent-hint
          class="mb-3"
        />
        <template v-else-if="type === 'switch'">
          <v-text-field
            v-model="switchId"
            data-field="menu-switch-id"
            :label="t('pages.dashboard.menu.fieldSwitchId', '开关 ID')"
            :hint="
              t(
                'pages.dashboard.menu.switchHint',
                '用户切换后，消息 ext 中会携带该 ID。',
              )
            "
            variant="outlined"
            density="compact"
            persistent-hint
            class="mb-3"
          />
          <v-switch
            v-model="switchDefault"
            data-field="menu-switch-default"
            color="primary"
            inset
            hide-details
            :label="t('pages.dashboard.menu.switchDefault', '默认开启')"
            class="mb-3"
          />
        </template>
        <div v-else class="qc-metric-note mb-3">
          {{
            t(
              'pages.dashboard.menu.menuHint',
              '子菜单本身不发送内容；保存后可继续为它添加发送消息或跳转链接子项。',
            )
          }}
        </div>

        <v-alert
          v-if="error"
          type="error"
          variant="tonal"
          density="compact"
          :prepend-icon="mdiAlertCircleOutline"
        >
          {{ error }}
        </v-alert>
      </v-card-text>

      <v-card-actions class="px-5 pb-5">
        <v-spacer />
        <v-btn variant="text" @click="close">
          {{ t('pages.dashboard.common.cancel', '取消') }}
        </v-btn>
        <v-btn color="primary" variant="tonal" data-field="menu-save" @click="onSave">
          {{ t('pages.dashboard.common.save', '保存') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
