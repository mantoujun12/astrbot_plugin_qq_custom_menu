<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  mdiAlertCircleOutline,
  mdiInformationOutline,
  mdiMenuDownOutline,
  mdiRefresh,
  mdiServerOutline,
  mdiTuneVariant,
} from '@mdi/js'
import { fetchStatus } from '../api/dashboard'
import PlatformStatusCard from '../components/status/PlatformStatusCard.vue'
import StatCard from '../components/status/StatCard.vue'
import SyncPanel from '../components/status/SyncPanel.vue'
import { useBridge } from '../composables/useBridge'
import type { StatusResponse } from '../types/dashboard'

const { t, ready, hasBackend } = useBridge()

const status = ref<StatusResponse | null>(null)
const loading = ref(false)
const error = ref('')

// 请求代次：初始加载与手动刷新可能重叠，只允许最新一次请求写回状态。
let loadSeq = 0

async function load(options: { refresh?: boolean } = {}): Promise<void> {
  const seq = ++loadSeq
  loading.value = true
  error.value = ''
  try {
    const next = await fetchStatus(options)
    if (seq !== loadSeq) return
    status.value = next
  } catch (err) {
    if (seq !== loadSeq) return
    status.value = null
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    if (seq === loadSeq) loading.value = false
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

const hasPlatforms = computed(() => (status.value?.platforms.length ?? 0) > 0)
const hasItems = computed(() => (status.value?.menu.total ?? 0) > 0)

// 本地 `pnpm dev` 没有 bridge，fetchStatus 会退回 mock；这里显式标注避免把假数据
// 当成真实状态，ready 之前不显示以防首屏闪烁。
const mockMode = computed(() => ready.value && !hasBackend.value)
</script>

<template>
  <v-container fluid class="qc-page pa-4 pa-md-6">
    <div class="qc-header">
      <div class="qc-header-main">
        <h1 class="qc-title">{{ t('pages.dashboard.status.title', '状态概览') }}</h1>
        <p class="qc-subtitle">
          {{
            t(
              'pages.dashboard.status.subtitle',
              '查看菜单配置、同步状态与各 QQ 平台的凭证情况。',
            )
          }}
        </p>
      </div>

      <div class="qc-header-actions">
        <v-btn
          variant="text"
          color="primary"
          :loading="loading"
          :prepend-icon="mdiRefresh"
          @click="load({ refresh: true })"
        >
          {{ t('pages.dashboard.status.refresh', '刷新') }}
        </v-btn>
      </div>
    </div>

    <SyncPanel v-if="ready" class="mb-2" @finished="load({ refresh: true })" />

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

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
          'pages.dashboard.status.mockHint',
          '本地开发环境：展示的是 mock 数据，未连接 AstrBot 后端。',
        )
      }}
    </v-alert>

    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
      :prepend-icon="mdiAlertCircleOutline"
    >
      {{ t('pages.dashboard.status.loadFailed', '获取状态失败') }}：{{ error }}
    </v-alert>

    <template v-if="status">
      <v-row>
        <v-col cols="12" sm="6" lg="4">
          <StatCard
            :icon="mdiServerOutline"
            :title="t('pages.dashboard.status.cards.platforms', 'QQ 平台')"
            :value="status.platforms.length"
          />
        </v-col>
        <v-col cols="12" sm="6" lg="4">
          <StatCard
            :icon="mdiMenuDownOutline"
            :title="t('pages.dashboard.status.cards.topLevel', '一级菜单')"
            :value="status.menu.top_level"
            :max="status.menu.top_level_max"
            emphasize-at-limit
          />
        </v-col>
        <v-col cols="12" sm="6" lg="4">
          <StatCard
            :icon="mdiServerOutline"
            :title="t('pages.dashboard.status.cards.subItems', '子项')"
            :value="status.menu.sub_items"
          />
        </v-col>
      </v-row>

      <v-alert
        v-if="status.sync_menu === false"
        type="info"
        variant="tonal"
        density="compact"
        class="my-4"
        :prepend-icon="mdiInformationOutline"
      >
        {{
          t(
            'pages.dashboard.status.syncDisabled',
            '「启动时同步」已关闭：插件只读取 QQ 私聊菜单，不会覆盖线上内容。',
          )
        }}
      </v-alert>

      <div v-if="!hasPlatforms" class="qc-empty-panel">
        <v-icon :icon="mdiTuneVariant" size="40" class="mb-2" />
        <div class="text-body-1 font-weight-medium">
          {{ t('pages.dashboard.status.empty.platforms.title', '还没有可用的 QQ 平台') }}
        </div>
        <p class="qc-metric-note">
          {{
            t(
            'pages.dashboard.status.empty.platforms.description',
            '到「机器人」页新增机器人，或在「兼容性」页填写旧版平台凭证。',
            )
          }}
        </p>
        <v-btn color="primary" variant="tonal" to="/robots" class="mt-2">
          {{ t('pages.dashboard.status.empty.platforms.action', '去配置机器人') }}
        </v-btn>
      </div>

      <template v-else>
        <v-alert
          v-if="!hasItems"
          type="warning"
          variant="tonal"
          class="my-4"
          :prepend-icon="mdiAlertCircleOutline"
        >
          {{
            t(
            'pages.dashboard.status.empty.menu.description',
            '尚未配置菜单条目；同步会清理已启用场景中的旧内容。',
            )
          }}
        </v-alert>

        <v-row class="mt-1">
          <v-col
            v-for="platform in status.platforms"
            :key="platform.pf_id"
            cols="12"
            md="6"
            xl="4"
          >
            <PlatformStatusCard :platform="platform" />
          </v-col>
        </v-row>
      </template>

    </template>
  </v-container>
</template>
