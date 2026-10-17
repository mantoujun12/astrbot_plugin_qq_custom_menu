<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  mdiAlertCircleOutline,
  mdiCheckCircleOutline,
  mdiContentSave,
  mdiInformationOutline,
  mdiPlus,
  mdiSync,
} from '@mdi/js'
import { fetchConfig, saveConfig } from '../api/dashboard'
import MenuEntryDialog from '../components/menu/MenuEntryDialog.vue'
import MenuTree from '../components/menu/MenuTree.vue'
import { useBridge } from '../composables/useBridge'
import { useSyncRun } from '../composables/useSyncRun'
import {
  buildMenuPayload,
  childEntries,
  cloneEntries,
  removeEntry,
  replaceEntry,
  topLevelEntries,
  validateMenu,
} from './menuForm'
import type { MenuEntry, PluginConfigResponse } from '../types/dashboard'

const { t, ready, hasBackend } = useBridge()
const router = useRouter()
const { start: startSync } = useSyncRun()

const config = ref<PluginConfigResponse | null>(null)
const entries = ref<MenuEntry[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const dialogOpen = ref(false)
const editing = ref<MenuEntry | null>(null)
const dialogParent = ref('')

/** 本地开发没有 bridge，页面只展示 mock 并禁用编辑，不允许假装保存成功 */
const mockMode = computed(() => ready.value && !hasBackend.value)
const editable = computed(() => config.value !== null && hasBackend.value && !saving.value)
const limits = computed(
  () => config.value?.limits ?? { top_level_max: 10, sub_items_max: 10 },
)
const menuNames = computed(() =>
  topLevelEntries(entries.value)
    .filter((entry) => entry.type === 'menu')
    .map((entry) => entry.name),
)
const topLevelCount = computed(() => topLevelEntries(entries.value).length)
const editingHasChildren = computed(
  () =>
    editing.value?.type === 'menu' &&
    childEntries(entries.value, editing.value.name).length > 0,
)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const next = await fetchConfig()
    config.value = next
    entries.value = cloneEntries(next.menu)
  } catch (err) {
    config.value = null
    entries.value = []
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

watch(
  [ready, hasBackend],
  ([isReady]) => {
    if (isReady) {
      void load()
    }
  },
  { immediate: true },
)

function openAddTop(): void {
  editing.value = null
  dialogParent.value = ''
  dialogOpen.value = true
}

function openAddChild(parent: string): void {
  editing.value = null
  dialogParent.value = parent
  dialogOpen.value = true
}

function openEdit(entry: MenuEntry): void {
  editing.value = entry
  dialogParent.value = entry.parent
  dialogOpen.value = true
}

function onSaveEntry(next: MenuEntry): void {
  if (editing.value) {
    entries.value = replaceEntry(entries.value, editing.value, next)
  } else {
    entries.value = [...entries.value, next]
  }
  dialogOpen.value = false
}

function onDelete(target: MenuEntry): void {
  entries.value = removeEntry(entries.value, target)
}

async function save(options: { sync?: boolean } = {}): Promise<void> {
  if (!hasBackend.value) {
    return
  }
  const checked = validateMenu(entries.value, limits.value, t)
  if (!checked.ok) {
    error.value = checked.reason
    notice.value = ''
    return
  }

  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const next = await saveConfig({ menu: buildMenuPayload(entries.value) })
    config.value = next
    entries.value = cloneEntries(next.menu)
    notice.value = t('views.dashboard.menu.saved', '菜单已保存并生效。')
    if (options.sync) {
      await startSync()
      await router.push({ name: 'status' })
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <v-container fluid class="qc-page pa-4 pa-md-6">
    <div class="qc-header">
      <div class="qc-header-main">
        <h1 class="qc-title">{{ t('views.dashboard.menu.title', '菜单配置') }}</h1>
        <p class="qc-subtitle">
          {{
            t(
              'views.dashboard.menu.subtitle',
              '维护 QQ 私聊菜单的一级菜单与子项；保存后会写回插件配置。',
            )
          }}
        </p>
      </div>

      <div class="qc-header-actions">
        <v-btn
          variant="text"
          color="primary"
          :loading="loading"
          :disabled="!hasBackend"
          @click="load"
        >
          {{ t('views.dashboard.common.reload', '重新载入') }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          :loading="saving"
          :disabled="!editable"
          :prepend-icon="mdiSync"
          @click="save({ sync: true })"
        >
          {{ t('views.dashboard.menu.saveAndSync', '保存并同步') }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          :loading="saving"
          :disabled="!editable"
          :prepend-icon="mdiContentSave"
          @click="save()"
        >
          {{ t('views.dashboard.common.save', '保存') }}
        </v-btn>
      </div>
    </div>

    <v-alert
      v-if="mockMode"
      type="info"
      variant="tonal"
      density="compact"
      class="mb-4"
      :prepend-icon="mdiInformationOutline"
    >
      {{
        t(
          'views.dashboard.menu.mockHint',
          '本地开发环境：展示的是 mock 数据，不能保存配置。',
        )
      }}
    </v-alert>

    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-4"
      :prepend-icon="mdiAlertCircleOutline"
    >
      {{ error }}
    </v-alert>

    <v-alert
      v-if="notice"
      type="success"
      variant="tonal"
      density="compact"
      class="mb-4"
      :prepend-icon="mdiCheckCircleOutline"
    >
      {{ notice }}
    </v-alert>

    <v-alert
      v-if="config && entries.length === 0"
      type="warning"
      variant="tonal"
      density="compact"
      class="mb-4"
      :prepend-icon="mdiAlertCircleOutline"
    >
      {{
        t(
          'views.dashboard.menu.emptyWarning',
          '菜单为空；在「启动时同步自定义菜单」开启时，同步会清空 QQ 上已有的自定义菜单。',
        )
      }}
    </v-alert>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <v-card v-if="config" class="qc-card" variant="outlined">
      <v-card-item class="px-5 pt-5">
        <v-card-title class="text-body-large">
          {{ t('views.dashboard.menu.listTitle', '菜单条目') }}
        </v-card-title>
        <v-card-subtitle>
          {{
            t(
              'views.dashboard.menu.listSubtitle',
              '一级菜单 {top}/{maxTop}；每个子菜单最多 {maxSub} 个子项。',
            )
              .replace('{top}', String(topLevelCount))
              .replace('{maxTop}', String(limits.top_level_max))
              .replace('{maxSub}', String(limits.sub_items_max))
          }}
        </v-card-subtitle>
        <template #append>
          <v-btn
            variant="tonal"
            color="primary"
            :disabled="!editable || topLevelCount >= limits.top_level_max"
            :prepend-icon="mdiPlus"
            @click="openAddTop"
          >
            {{ t('views.dashboard.menu.addTop', '添加一级菜单') }}
          </v-btn>
        </template>
      </v-card-item>

      <v-card-text class="px-5 pb-5 pt-2">
        <MenuTree
          :entries="entries"
          @add-child="openAddChild"
          @edit="openEdit"
          @delete="onDelete"
        />
      </v-card-text>
    </v-card>

    <MenuEntryDialog
      v-model="dialogOpen"
      :entry="editing"
      :parent="dialogParent"
      :menu-names="menuNames"
      :has-children="editingHasChildren"
      @save="onSaveEntry"
    />
  </v-container>
</template>
