<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  mdiAlertCircleOutline,
  mdiCheckCircleOutline,
  mdiContentSave,
  mdiInformationOutline,
  mdiPlus,
  mdiTrashCanOutline,
} from '@mdi/js'
import { fetchConfig, saveConfig } from '../api/dashboard'
import { useBridge } from '../composables/useBridge'
import {
  PLATFORM_TYPES,
  buildPlatformPayload,
  newPlatform,
  toPlatformForm,
  validatePlatforms,
  type PlatformFormRow,
} from './platformForm'
import type { PluginConfigResponse } from '../types/dashboard'

const { t, ready, hasBackend } = useBridge()

const config = ref<PluginConfigResponse | null>(null)
const rows = ref<PlatformFormRow[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const mockMode = computed(() => ready.value && !hasBackend.value)
const editable = computed(() => config.value !== null && hasBackend.value && !saving.value)

const platformTypeItems = computed(() =>
  PLATFORM_TYPES.map((value) => ({
    title:
      value === 'qq_official'
        ? t('pages.dashboard.platforms.type.qq_official', 'QQ 官方机器人')
        : t('pages.dashboard.platforms.type.qq_official_webhook', 'QQ 官方机器人 Webhook'),
    value,
  })),
)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const next = await fetchConfig()
    config.value = next
    rows.value = toPlatformForm(next.qq_platforms)
  } catch (err) {
    config.value = null
    rows.value = []
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

function addRow(): void {
  rows.value = [...rows.value, newPlatform()]
}

function removeRow(index: number): void {
  rows.value = rows.value.filter((_, current) => current !== index)
}

async function save(): Promise<void> {
  if (!hasBackend.value) {
    return
  }
  const checked = validatePlatforms(rows.value, t)
  if (!checked.ok) {
    error.value = checked.reason
    notice.value = ''
    return
  }

  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const next = await saveConfig({ qq_platforms: buildPlatformPayload(rows.value) })
    config.value = next
    rows.value = toPlatformForm(next.qq_platforms)
    notice.value = t('pages.dashboard.platforms.saved', '机器人凭证已保存并生效。')
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
        <h1 class="qc-title">{{ t('pages.dashboard.platforms.title', '机器人') }}</h1>
        <p class="qc-subtitle">
          {{
            t(
              'pages.dashboard.platforms.subtitle',
              '每台 QQ 官方机器人独立维护 AppID 与 ClientSecret。',
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
          :loading="saving"
          :disabled="!editable"
          :prepend-icon="mdiContentSave"
          @click="save"
        >
          {{ t('pages.dashboard.common.save', '保存') }}
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
          'pages.dashboard.platforms.mockHint',
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

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <template v-if="config">
      <div v-if="rows.length === 0" class="qc-empty-panel mb-4">
        <v-icon :icon="mdiInformationOutline" size="40" class="mb-2" />
        <div class="text-body-1 font-weight-medium">
          {{ t('pages.dashboard.platforms.empty', '还没有插件配置的机器人') }}
        </div>
        <p class="qc-metric-note">
          {{
            t(
              'pages.dashboard.platforms.emptyHint',
              '添加 AppID 与 ClientSecret 后，插件启动时会同步这些机器人的菜单。',
            )
          }}
        </p>
      </div>

      <v-row>
        <v-col v-for="(row, index) in rows" :key="index" cols="12" md="6">
          <v-card class="qc-card h-100" variant="outlined">
            <v-card-item class="px-5 pt-5">
              <v-card-title class="text-body-large">
                {{
                  row.appid
                    ? row.appid
                    : t('pages.dashboard.platforms.newTitle', '新机器人')
                }}
              </v-card-title>
              <v-card-subtitle>
                {{
                  row.isNew
                    ? t('pages.dashboard.platforms.newSubtitle', '填写凭证后保存')
                    : t('pages.dashboard.platforms.savedSubtitle', '已保存的凭证')
                }}
              </v-card-subtitle>
              <template #append>
                <v-btn
                  icon
                  variant="text"
                  color="error"
                  :disabled="!editable"
                  :aria-label="t('pages.dashboard.common.delete', '删除')"
                  @click="removeRow(index)"
                >
                  <v-icon :icon="mdiTrashCanOutline" size="18" />
                </v-btn>
              </template>
            </v-card-item>

            <v-card-text class="px-5 pb-5 pt-3">
              <v-text-field
                v-model="row.appid"
                data-field="platform-appid"
                :label="t('pages.dashboard.platforms.appid', 'AppID')"
                variant="outlined"
                density="compact"
                class="mb-3"
                hide-details
                :disabled="!editable"
              />
              <v-text-field
                v-model="row.secret"
                data-field="platform-secret"
                :label="t('pages.dashboard.platforms.secret', 'ClientSecret')"
                :placeholder="
                  row.secret_set
                    ? t(
                        'pages.dashboard.platforms.secretPlaceholder',
                        '{masked}（留空表示沿用）',
                      ).replace('{masked}', row.secret_masked)
                    : ''
                "
                type="password"
                variant="outlined"
                density="compact"
                class="mb-3"
                hide-details
                :disabled="!editable"
              />
              <v-select
                v-model="row.platform"
                :items="platformTypeItems"
                :label="t('pages.dashboard.platforms.platform', '平台类型')"
                variant="outlined"
                density="compact"
                hide-details
                :disabled="!editable"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-btn
        variant="tonal"
        color="primary"
        data-field="platform-add"
        :disabled="!editable"
        :prepend-icon="mdiPlus"
        class="mt-4"
        @click="addRow"
      >
        {{ t('pages.dashboard.platforms.add', '添加机器人') }}
      </v-btn>

      <v-card
        v-if="config.runtime_platforms.length"
        class="qc-card mt-6"
        variant="outlined"
      >
        <v-card-item class="px-5 pt-5">
          <v-card-title class="text-body-large">
            {{ t('pages.dashboard.platforms.runtimeTitle', '当前生效的平台') }}
          </v-card-title>
          <v-card-subtitle>
            {{
              t(
                'pages.dashboard.platforms.runtimeSubtitle',
                '启动同步与状态页使用这份列表。',
              )
            }}
          </v-card-subtitle>
        </v-card-item>
        <v-card-text class="px-5 pb-5 pt-2">
          <div
            v-for="platform in config.runtime_platforms"
            :key="platform.pf_id"
            class="qc-list-row"
          >
            <div class="qc-row-main">
              <div class="qc-list-label">{{ platform.pf_id }}</div>
              <div class="qc-metric-note">
                {{ platform.platform }} ·
                {{ t('pages.dashboard.platforms.sourcePlugin', '插件配置') }}
              </div>
            </div>
            <v-chip
              size="small"
              variant="tonal"
              :color="platform.secret_set ? 'success' : 'error'"
            >
              {{
                platform.secret_set
                  ? t('pages.dashboard.status.secretSet', '已配置')
                  : t('pages.dashboard.status.secretMissing', '未配置')
              }}
            </v-chip>
          </div>
        </v-card-text>
      </v-card>
    </template>
  </v-container>
</template>
