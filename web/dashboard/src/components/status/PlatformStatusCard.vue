<script setup lang="ts">
import { useBridge } from '../../composables/useBridge'
import type { PlatformStatus, SyncState } from '../../types/dashboard'

defineProps<{ platform: PlatformStatus }>()

const { t } = useBridge()

const STATE_META: Record<SyncState, { color: string; fallback: string }> = {
  synced: { color: 'success', fallback: '已同步' },
  pending: { color: 'warning', fallback: '待同步' },
  unknown: { color: 'info', fallback: '尚未同步' },
  disabled: { color: 'grey', fallback: '同步已关闭' },
}

function stateColor(state: SyncState): string {
  return STATE_META[state].color
}

function stateLabel(state: SyncState): string {
  return t(`pages.dashboard.status.state.${state}`, STATE_META[state].fallback)
}

function sourceLabel(source: PlatformStatus['source']): string {
  if (source === 'robot') {
    return t('pages.dashboard.status.source.robot', '机器人')
  }
  if (source === 'compatibility') {
    return t('pages.dashboard.status.source.compatibility', '兼容性配置')
  }
  return t('pages.dashboard.status.source.robot', '机器人')
}

function sceneLabel(scene: string): string {
  return t('pages.dashboard.robots.scene.c2c', scene === 'c2c' ? '私聊' : scene)
}
</script>

<template>
  <v-card class="qc-card h-100" variant="outlined">
    <v-card-item class="px-5 pt-5">
      <v-card-title class="text-body-large" data-field="robot-title">
        {{ platform.name || platform.pf_id }}
      </v-card-title>
      <v-card-subtitle class="d-flex align-center ga-2">
        <span>{{ platform.platform }}</span>
        <v-chip data-field="config-source" size="x-small" variant="tonal">
          {{ sourceLabel(platform.source) }}
        </v-chip>
      </v-card-subtitle>
    </v-card-item>

    <v-card-text class="px-5 pb-4 pt-3">
      <div class="qc-list-row">
        <div class="qc-row-main">
          <div class="qc-list-label">appid</div>
          <div class="qc-metric-note">{{ platform.appid }}</div>
        </div>
        <v-chip size="small" variant="tonal" :color="stateColor(platform.state)">
          {{ stateLabel(platform.state) }}
        </v-chip>
      </div>
      <div
        v-for="scene in platform.scenes ?? []"
        :key="scene.scene"
        class="qc-list-row"
        data-field="platform-scene"
      >
        <div class="qc-row-main">
          <div class="qc-list-label">{{ sceneLabel(scene.scene) }}</div>
          <div class="qc-metric-note">
            {{ scene.item_count }}
            {{ t('pages.dashboard.status.itemUnit', '项') }}
          </div>
        </div>
        <v-chip size="small" variant="tonal" :color="stateColor(scene.state)">
          {{ stateLabel(scene.state) }}
        </v-chip>
      </div>
      <div class="qc-list-row">
        <div class="qc-list-label">
          {{ t('pages.dashboard.status.secret', 'ClientSecret') }}
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
