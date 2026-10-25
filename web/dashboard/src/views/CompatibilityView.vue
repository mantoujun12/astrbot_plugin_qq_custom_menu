<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  mdiAlertCircleOutline,
  mdiContentSave,
  mdiInformationOutline,
  mdiPlus,
  mdiSync,
  mdiTrashCanOutline,
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
import {
  PLATFORM_TYPES,
  buildPlatformPayload,
  newPlatform,
  toPlatformForm,
  validatePlatforms,
  type PlatformFormRow,
} from './platformForm'
import type { MenuEntry, PluginConfigResponse } from '../types/dashboard'

const { t, ready, hasBackend } = useBridge()
const router = useRouter()
const { start: startSync } = useSyncRun()

const config = ref<PluginConfigResponse | null>(null)
const platforms = ref<PlatformFormRow[]>([])
const entries = ref<MenuEntry[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const dialogOpen = ref(false)
const editing = ref<MenuEntry | null>(null)
const dialogParent = ref('')

const mockMode = computed(() => ready.value && !hasBackend.value)
const editable = computed(
  () => config.value !== null && hasBackend.value && !saving.value,
)
const limits = computed(
  () => config.value?.limits ?? { top_level_max: 10, sub_items_max: 5 },
)
const topLevelCount = computed(() => topLevelEntries(entries.value).length)
const editingHasChildren = computed(
  () =>
    editing.value?.type === 'menu' &&
    childEntries(entries.value, editing.value.name).length > 0,
)
const platformItems = computed(() =>
  PLATFORM_TYPES.map((value) => ({
    value,
    title:
      value === 'qq_official'
        ? t(
            'pages.dashboard.compatibility.platformTypeName.qq_official',
            'QQ 官方机器人',
          )
        : t(
            'pages.dashboard.compatibility.platformTypeName.qq_official_webhook',
            'QQ 官方机器人 Webhook',
          ),
  })),
)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    const next = await fetchConfig()
    config.value = next
    platforms.value = toPlatformForm(next.qq_platforms)
    entries.value = cloneEntries(next.menu)
  } catch (err) {
    config.value = null
    platforms.value = []
    entries.value = []
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

watch(
  [ready, hasBackend],
  ([isReady]) => {
    if (isReady) void load()
  },
  { immediate: true },
)

function addPlatform(): void {
  platforms.value = [...platforms.value, newPlatform()]
}

function removePlatform(index: number): void {
  platforms.value = platforms.value.filter((_, current) => current !== index)
}

function openAdd(parent = ''): void {
  editing.value = null
  dialogParent.value = parent
  dialogOpen.value = true
}

function openEdit(entry: MenuEntry): void {
  editing.value = entry
  dialogParent.value = entry.parent
  dialogOpen.value = true
}

function saveEntry(next: MenuEntry): void {
  entries.value = editing.value
    ? replaceEntry(entries.value, editing.value, next)
    : [...entries.value, next]
}

function deleteEntry(entry: MenuEntry): void {
  entries.value = removeEntry(entries.value, entry)
}

async function save(options: { sync?: boolean } = {}): Promise<void> {
  if (!hasBackend.value) return
  const checkedPlatforms = validatePlatforms(platforms.value, t)
  if (!checkedPlatforms.ok) {
    error.value = checkedPlatforms.reason
    notice.value = ''
    return
  }
  const checkedMenu = validateMenu(entries.value, limits.value, t)
  if (!checkedMenu.ok) {
    error.value = checkedMenu.reason
    notice.value = ''
    return
  }

  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const next = await saveConfig({
      qq_platforms: buildPlatformPayload(platforms.value),
      menu: buildMenuPayload(entries.value),
    })
    config.value = next
    platforms.value = toPlatformForm(next.qq_platforms)
    entries.value = cloneEntries(next.menu)
    notice.value = t(
      'pages.dashboard.compatibility.saved',
      '兼容性配置已保存。',
    )
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
    return
  } finally {
    saving.value = false
  }

  if (options.sync) {
    try {
      await startSync()
      await router.push({ name: 'status' })
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    }
  }
}
</script>

<template>
  <v-container fluid class="qc-page pa-4 pa-md-6">
    <div class="qc-header">
      <div class="qc-header-main">
        <h1 class="qc-title">
          {{ t('pages.dashboard.compatibility.title', '兼容性配置') }}
        </h1>
        <p class="qc-subtitle">
          {{
            t(
              'pages.dashboard.compatibility.subtitle',
              '保留旧版全局私聊菜单与凭证。已被「机器人」按 AppID 接管的机器人不会读取这里的菜单。',
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
          {{ t('pages.dashboard.common.reload', '重新载入') }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          :prepend-icon="mdiContentSave"
          :loading="saving"
          :disabled="!editable"
          @click="save()"
        >
          {{ t('pages.dashboard.common.save', '保存') }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          :prepend-icon="mdiSync"
          :loading="saving"
          :disabled="!editable"
          @click="save({ sync: true })"
        >
          {{ t('pages.dashboard.compatibility.saveAndSync', '保存并同步') }}
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
          'pages.dashboard.compatibility.mockHint',
          '本地开发环境：展示 mock 数据，不能保存配置。',
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
    >
      {{ notice }}
    </v-alert>
    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <template v-if="config">
      <v-card class="qc-card mb-4" variant="outlined">
        <v-card-item class="px-5 pt-5">
          <v-card-title class="text-body-large">
            {{ t('pages.dashboard.compatibility.platformsTitle', '兼容平台凭证') }}
          </v-card-title>
          <v-card-subtitle>
            {{
              t(
                'pages.dashboard.compatibility.platformsSubtitle',
                'ClientSecret 留空表示沿用已保存的密钥。',
              )
            }}
          </v-card-subtitle>
          <template #append>
            <v-btn
              variant="tonal"
              color="primary"
              size="small"
              :prepend-icon="mdiPlus"
              :disabled="!editable"
              @click="addPlatform"
            >
              {{ t('pages.dashboard.compatibility.addPlatform', '添加平台') }}
            </v-btn>
          </template>
        </v-card-item>
        <v-card-text class="px-5 pb-5 pt-2">
          <div v-if="!platforms.length" class="qc-metric-note mb-3">
            {{
              t(
                'pages.dashboard.compatibility.noPlatforms',
                '还没有兼容平台凭证。',
              )
            }}
          </div>
          <v-card
            v-for="(row, index) in platforms"
            :key="index"
            class="qc-config-item mb-3"
            variant="flat"
          >
            <v-row>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="row.appid"
                  data-field="platform-appid"
                  label="AppID"
                  variant="outlined"
                  density="compact"
                  hide-details
                  :disabled="!editable"
                />
              </v-col>
              <v-col cols="12" md="5">
                <v-text-field
                  v-model="row.secret"
                  data-field="platform-secret"
                  type="password"
                  :placeholder="row.secret_set ? row.secret_masked : ''"
                  label="ClientSecret"
                  variant="outlined"
                  density="compact"
                  hide-details
                  :disabled="!editable"
                />
              </v-col>
              <v-col cols="12" md="2">
                <v-select
                  v-model="row.platform"
                  :items="platformItems"
                  :label="t('pages.dashboard.compatibility.platformType', '平台类型')"
                  variant="outlined"
                  density="compact"
                  hide-details
                  :disabled="!editable"
                />
              </v-col>
              <v-col cols="12" md="1" class="d-flex align-center justify-end">
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  color="error"
                  :disabled="!editable"
                  :aria-label="t('pages.dashboard.common.delete', '删除')"
                  @click="removePlatform(index)"
                >
                  <v-icon :icon="mdiTrashCanOutline" size="20" />
                </v-btn>
              </v-col>
            </v-row>
          </v-card>
        </v-card-text>
      </v-card>

      <v-card class="qc-card" variant="outlined">
        <v-card-item class="px-5 pt-5">
          <v-card-title class="text-body-large">
            {{ t('pages.dashboard.compatibility.menuTitle', '兼容私聊菜单') }}
          </v-card-title>
          <v-card-subtitle>
            {{
              t(
                'pages.dashboard.compatibility.menuSubtitle',
                '一级菜单 {top}/{maxTop}；每个子菜单最多 {maxSub} 项。',
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
              size="small"
              :prepend-icon="mdiPlus"
              :disabled="!editable || topLevelCount >= limits.top_level_max"
              @click="openAdd()"
            >
              {{ t('pages.dashboard.compatibility.addMenu', '添加一级菜单') }}
            </v-btn>
          </template>
        </v-card-item>
        <v-card-text class="px-5 pb-5 pt-2">
          <v-alert
            v-if="entries.length === 0"
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            {{
              t(
                'pages.dashboard.compatibility.emptyWarning',
                '兼容菜单为空；同步开启时会清空未被新版机器人接管的 QQ 自定义菜单。',
              )
            }}
          </v-alert>
          <MenuTree
            :entries="entries"
            @add-child="openAdd"
            @edit="openEdit"
            @delete="deleteEntry"
          />
        </v-card-text>
      </v-card>
    </template>

    <MenuEntryDialog
      v-model="dialogOpen"
      :entry="editing"
      :parent="dialogParent"
      :has-children="editingHasChildren"
      @save="saveEntry"
    />
  </v-container>
</template>
