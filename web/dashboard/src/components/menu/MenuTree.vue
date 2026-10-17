<script setup lang="ts">
import { computed } from 'vue'
import {
  mdiLinkVariant,
  mdiMenuDownOutline,
  mdiMessageTextOutline,
  mdiPencilOutline,
  mdiPlus,
  mdiTrashCanOutline,
} from '@mdi/js'
import { useBridge } from '../../composables/useBridge'
import { childEntries, topLevelEntries } from '../../views/menuForm'
import type { MenuEntry } from '../../types/dashboard'

const props = defineProps<{
  entries: MenuEntry[]
  /** 只读模式用于状态页预览，不显示操作按钮 */
  readonly?: boolean
}>()

defineEmits<{
  addChild: [parent: string]
  edit: [entry: MenuEntry]
  delete: [entry: MenuEntry]
}>()

const { t } = useBridge()

const groups = computed(() =>
  topLevelEntries(props.entries).map((entry) => ({
    entry,
    children: childEntries(props.entries, entry.name),
  })),
)

const TYPE_META = {
  send_message: {
    icon: mdiMessageTextOutline,
    labelKey: 'views.dashboard.menu.type.send_message',
    fallback: '发送消息',
  },
  link: {
    icon: mdiLinkVariant,
    labelKey: 'views.dashboard.menu.type.link',
    fallback: '跳转链接',
  },
  menu: {
    icon: mdiMenuDownOutline,
    labelKey: 'views.dashboard.menu.type.menu',
    fallback: '子菜单',
  },
} as const

function typeLabel(entry: MenuEntry): string {
  return t(TYPE_META[entry.type].labelKey, TYPE_META[entry.type].fallback)
}

function detail(entry: MenuEntry): string {
  if (entry.type === 'send_message') {
    return entry.message ? `→ ${entry.message}` : ''
  }
  if (entry.type === 'link') {
    return entry.link ?? ''
  }
  return t('views.dashboard.menu.childCount', '{count} 个子项').replace(
    '{count}',
    String(childEntries(props.entries, entry.name).length),
  )
}
</script>

<template>
  <div class="qc-menu-tree">
    <div v-if="groups.length === 0" class="qc-metric-note qc-menu-empty">
      {{ t('views.dashboard.menu.empty', '还没有菜单条目') }}
    </div>

    <div v-for="group in groups" :key="group.entry.name" class="qc-menu-group">
      <div class="qc-menu-row" data-field="menu-row">
        <v-icon :icon="TYPE_META[group.entry.type].icon" size="18" class="qc-menu-icon" />
        <div class="qc-menu-main">
          <div class="qc-menu-name">{{ group.entry.name }}</div>
          <div class="qc-menu-detail">
            <span>{{ typeLabel(group.entry) }}</span>
            <span v-if="detail(group.entry)"> · {{ detail(group.entry) }}</span>
          </div>
        </div>
        <div v-if="!readonly" class="qc-menu-actions">
          <v-btn
            v-if="group.entry.type === 'menu'"
            icon
            variant="text"
            size="small"
            :aria-label="t('views.dashboard.menu.addChild', '添加子项')"
            @click="$emit('addChild', group.entry.name)"
          >
            <v-icon :icon="mdiPlus" size="18" />
          </v-btn>
          <v-btn
            icon
            variant="text"
            size="small"
            :aria-label="t('views.dashboard.menu.edit', '编辑')"
            @click="$emit('edit', group.entry)"
          >
            <v-icon :icon="mdiPencilOutline" size="18" />
          </v-btn>
          <v-btn
            icon
            variant="text"
            size="small"
            color="error"
            :aria-label="t('views.dashboard.menu.delete', '删除')"
            @click="$emit('delete', group.entry)"
          >
            <v-icon :icon="mdiTrashCanOutline" size="18" />
          </v-btn>
        </div>
      </div>

      <div v-if="group.children.length" class="qc-menu-children">
        <div
          v-for="child in group.children"
          :key="`${group.entry.name}-${child.name}`"
          class="qc-menu-row qc-menu-row--child"
          data-field="menu-child-row"
        >
          <v-icon :icon="TYPE_META[child.type].icon" size="16" class="qc-menu-icon" />
          <div class="qc-menu-main">
            <div class="qc-menu-name">{{ child.name }}</div>
            <div class="qc-menu-detail">
              <span>{{ typeLabel(child) }}</span>
              <span v-if="detail(child)"> · {{ detail(child) }}</span>
            </div>
          </div>
          <div v-if="!readonly" class="qc-menu-actions">
            <v-btn
              icon
              variant="text"
              size="small"
              :aria-label="t('views.dashboard.menu.edit', '编辑')"
              @click="$emit('edit', child)"
            >
              <v-icon :icon="mdiPencilOutline" size="18" />
            </v-btn>
            <v-btn
              icon
              variant="text"
              size="small"
              color="error"
              :aria-label="t('views.dashboard.menu.delete', '删除')"
              @click="$emit('delete', child)"
            >
              <v-icon :icon="mdiTrashCanOutline" size="18" />
            </v-btn>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
