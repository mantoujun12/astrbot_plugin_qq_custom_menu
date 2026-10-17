<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  mdiAlertCircleOutline,
  mdiFormatListBulleted,
  mdiInformationOutline,
  mdiMenuDownOutline,
  mdiRefresh,
  mdiRobotOutline,
  mdiServerOutline,
  mdiTuneVariant,
} from '@mdi/js'
import { fetchStatus } from '../api/dashboard'
import MenuTree from '../components/menu/MenuTree.vue'
import PlatformStatusCard from '../components/status/PlatformStatusCard.vue'
import StatCard from '../components/status/StatCard.vue'
import SyncPanel from '../components/status/SyncPanel.vue'
import { useBridge } from '../composables/useBridge'
import { qqItemsToEntries } from './menuForm'
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
const previewEntries = computed(() =>
  status.value ? qqItemsToEntries(status.value.menu.items) : [],
)

// 本地 `pnpm dev` 没有 bridge，fetchStatus 会退回 mock；这里显式标注避免把假数据
// 当成真实状态，ready 之前不显示以防首屏闪烁。
const mockMode = computed(() => ready.value && !hasBackend.value)
const usingFallback = computed(
  () => status.value?.platforms.some((platform) => platform.source === 'astrbot') ?? false,
)
</script>

<template>
  <v-container fluid class="qc-page pa-4 pa-md-6">
    <div class="qc-header">
      <div class="qc-header-main">
        <h1 class="qc-title">{{ t('views.dashboard.status.title', '状态概览') }}</h1>
        <p class="qc-subtitle">
          {{
            t(
              'views.dashboard.status.subtitle',
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
          {{ t('views.dashboard.status.refresh', '刷新') }}
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
          'views.dashboard.status.mockHint',
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
      {{ t('views.dashboard.status.loadFailed', '获取状态失败') }}：{{ error }}
    </v-alert>

    <template v-if="status">
      <v-row>
        <v-col cols="12" sm="6" lg="3">
          <StatCard
            :icon="mdiServerOutline"
            :title="t('views.dashboard.status.cards.platforms', 'QQ 平台')"
            :value="status.platforms.length"
          />
        </v-col>
        <v-col cols="12" sm="6" lg="3">
          <StatCard
            :icon="mdiMenuDownOutline"
            :title="t('views.dashboard.status.cards.topLevel', '一级菜单')"
            :value="status.menu.top_level"
            :max="status.menu.top_level_max"
            emphasize-at-limit
          />
        </v-col>
        <v-col cols="12" sm="6" lg="3">
          <StatCard
            :icon="mdiFormatListBulleted"
            :title="t('views.dashboard.status.cards.subItems', '子项')"
            :value="status.menu.sub_items"
          />
        </v-col>
        <v-col cols="12" sm="6" lg="3">
          <StatCard
            :icon="mdiRobotOutline"
            :title="t('views.dashboard.status.cards.total', '菜单条目')"
            :value="status.menu.total"
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
            'views.dashboard.status.syncDisabled',
            '「启动时同步自定义菜单」已关闭：插件只会读取 QQ 菜单，不会覆盖线上内容。',
          )
        }}
      </v-alert>

      <v-alert
        v-if="usingFallback"
        type="info"
        variant="tonal"
        density="compact"
        class="my-4"
        :prepend-icon="mdiInformationOutline"
      >
        {{
          t(
            'views.dashboard.status.fallbackHint',
            '当前平台凭证来自 AstrBot 平台配置，只能查看；在「机器人」页添加插件配置后会优先使用插件凭证。',
          )
        }}
      </v-alert>

      <div v-if="!hasPlatforms" class="qc-empty-panel">
        <v-icon :icon="mdiTuneVariant" size="40" class="mb-2" />
        <div class="text-body-1 font-weight-medium">
          {{ t('views.dashboard.status.empty.platforms.title', '还没有可用的 QQ 平台') }}
        </div>
        <p class="qc-metric-note">
          {{
            t(
              'views.dashboard.status.empty.platforms.description',
              '到「机器人」页填写 AppID 与 ClientSecret，或在 AstrBot 平台配置里启用 QQ 官方机器人。',
            )
          }}
        </p>
        <v-btn color="primary" variant="tonal" to="/platforms" class="mt-2">
          {{ t('views.dashboard.status.empty.platforms.action', '去配置机器人') }}
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
              'views.dashboard.status.empty.menu.description',
              '尚未配置菜单条目；同步会清空 QQ 上已有的自定义菜单。',
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

      <v-card class="qc-card mt-4" variant="outlined">
        <v-card-item class="px-5 pt-5">
          <v-card-title class="text-body-large">
            {{ t('views.dashboard.status.previewTitle', '菜单预览') }}
          </v-card-title>
          <v-card-subtitle>
            {{
              t(
                'views.dashboard.status.previewSubtitle',
                '这是插件将写入 QQ 的菜单结构。',
              )
            }}
          </v-card-subtitle>
          <template #append>
            <v-btn variant="text" color="primary" to="/menu">
              {{ t('views.dashboard.status.editMenu', '编辑菜单') }}
            </v-btn>
          </template>
        </v-card-item>
        <v-card-text class="px-5 pb-5 pt-2">
          <MenuTree :entries="previewEntries" readonly />
        </v-card-text>
      </v-card>
    </template>
  </v-container>
</template>
