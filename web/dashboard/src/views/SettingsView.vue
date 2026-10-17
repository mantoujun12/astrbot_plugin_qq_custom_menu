<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  mdiAlertCircleOutline,
  mdiCheckCircleOutline,
  mdiContentSave,
  mdiGithub,
  mdiInformationOutline,
} from '@mdi/js'
import { fetchConfig, saveConfig } from '../api/dashboard'
import { useBridge } from '../composables/useBridge'
import { PLUGIN_VERSION } from '../version'
import type { PluginConfigResponse } from '../types/dashboard'

const { t, ready, hasBackend } = useBridge()

const GITHUB_REPOSITORY_URL =
  'https://github.com/mantoujun12/astrbot_plugin_qq_custom_menu'

const LANGUAGE_OPTIONS = computed(() => [
  { title: t('views.dashboard.settings.languageName.zh-CN', '简体中文'), value: 'zh-CN' },
  { title: t('views.dashboard.settings.languageName.en-US', 'English'), value: 'en-US' },
])

const config = ref<PluginConfigResponse | null>(null)
const language = ref('zh-CN')
const syncMenu = ref(true)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const mockMode = computed(() => ready.value && !hasBackend.value)
const editable = computed(() => config.value !== null && hasBackend.value && !saving.value)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const next = await fetchConfig()
    config.value = next
    language.value = next.language
    syncMenu.value = next.sync_menu
  } catch (err) {
    config.value = null
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

async function save(): Promise<void> {
  if (!hasBackend.value) {
    return
  }
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const next = await saveConfig({
      language: language.value,
      sync_menu: syncMenu.value,
    })
    config.value = next
    language.value = next.language
    syncMenu.value = next.sync_menu
    notice.value = t('views.dashboard.settings.saved', '设置已保存并生效。')
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
        <h1 class="qc-title">{{ t('views.dashboard.settings.title', '设置') }}</h1>
        <p class="qc-subtitle">
          {{
            t(
              'views.dashboard.settings.subtitle',
              '插件级通用设置：日志语言与启动同步开关。',
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
          :prepend-icon="mdiContentSave"
          @click="save"
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
          'views.dashboard.settings.mockHint',
          '本地开发环境：可编辑预览，但不能保存配置。',
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

    <v-card v-if="config" class="qc-card mb-4" variant="outlined">
      <v-card-item class="px-5 pt-5">
        <v-card-title class="text-body-large">
          {{ t('views.dashboard.settings.basicTitle', '基础配置') }}
        </v-card-title>
        <v-card-subtitle>
          {{ t('views.dashboard.settings.basicSubtitle', '日志语言只影响插件日志。') }}
        </v-card-subtitle>
      </v-card-item>

      <v-card-text class="px-5 pb-5 pt-3">
        <v-select
          v-model="language"
          data-field="settings-language"
          :items="LANGUAGE_OPTIONS"
          :disabled="!editable"
          :label="t('views.dashboard.settings.language', '日志语言')"
          variant="outlined"
          density="compact"
          class="mb-4"
          hide-details
        />
        <v-switch
          v-model="syncMenu"
          data-field="settings-sync-menu"
          :disabled="!editable"
          :label="t('views.dashboard.settings.syncMenu', '启动时同步自定义菜单')"
          :hint="
            t(
              'views.dashboard.settings.syncMenuHint',
              '关闭后插件只读取 QQ 当前菜单，不会覆盖线上内容。',
            )
          "
          persistent-hint
          color="primary"
          inset
          hide-details="auto"
        />
      </v-card-text>
    </v-card>

    <v-card v-if="config" class="qc-card qc-about-plugin" variant="outlined">
      <v-card-item class="px-5 pt-5">
        <v-card-title class="text-body-large">
          {{ t('views.dashboard.settings.aboutTitle', '关于插件') }}
        </v-card-title>
        <v-card-subtitle>
          {{ t('views.dashboard.settings.aboutSubtitle', '插件简介与仓库入口。') }}
        </v-card-subtitle>
      </v-card-item>

      <v-card-text class="px-5 pb-5 pt-3">
        <div class="d-flex flex-wrap align-center justify-space-between gap-4">
          <div>
            <div class="text-body-1 font-weight-medium">
              {{ t('views.dashboard.settings.aboutName', 'QQ 自定义菜单') }}
            </div>
            <p class="text-body-2 text-medium-emphasis mt-1 mb-0">
              {{
                t(
                  'views.dashboard.settings.aboutDescription',
                  '在 AstrBot WebUI 维护菜单条目，并同步到 QQ 官方机器人私聊菜单。',
                )
              }}
            </p>
          </div>
          <v-chip class="qc-about-version" color="primary" variant="tonal">
            {{ PLUGIN_VERSION }}
          </v-chip>
        </div>
      </v-card-text>

      <v-card-text class="px-5 pb-5 pt-3">
        <div class="d-flex flex-wrap align-center justify-space-between gap-4">
          <div>
            <div class="text-body-1 font-weight-medium">
              {{ t('views.dashboard.settings.githubTitle', 'GitHub 仓库') }}
            </div>
            <p class="text-body-2 text-medium-emphasis mt-1 mb-0">
              {{
                t(
                  'views.dashboard.settings.githubDescription',
                  '查看项目源码、更新日志与问题反馈。',
                )
              }}
            </p>
          </div>
          <v-btn
            class="qc-github-link"
            :href="GITHUB_REPOSITORY_URL"
            target="_blank"
            rel="noopener noreferrer"
            color="primary"
            variant="tonal"
            :prepend-icon="mdiGithub"
          >
            {{ t('views.dashboard.settings.githubAction', '访问 GitHub') }}
          </v-btn>
        </div>
      </v-card-text>
    </v-card>
  </v-container>
</template>
