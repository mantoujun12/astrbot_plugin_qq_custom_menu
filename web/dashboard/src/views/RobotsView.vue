<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  mdiAccountOutline,
  mdiAlertCircleOutline,
  mdiContentSave,
  mdiImport,
  mdiInformationOutline,
  mdiPlus,
  mdiRobotOutline,
  mdiSync,
  mdiTrashCanOutline,
} from '@mdi/js'
import { fetchConfig } from '../api/dashboard'
import {
  fetchRobots,
  importLegacyRobots,
  saveRobots,
} from '../api/robots'
import MenuEntryDialog from '../components/menu/MenuEntryDialog.vue'
import MenuTree from '../components/menu/MenuTree.vue'
import { useBridge } from '../composables/useBridge'
import { useSyncRun } from '../composables/useSyncRun'
import { childEntries, removeEntry, replaceEntry } from './menuForm'
import {
  emptyRobotForm,
  robotItemCount,
  robotSceneCount,
  toRobotForm,
  validateRobotForm,
} from './robotForm'
import type { MenuEntry } from '../types/dashboard'
import type {
  RobotConfig,
  RobotConfigForm,
  RobotConfigPayload,
  RobotConfigResponse,
} from '../types/robotConfig'

interface RobotDraft {
  key: string
  form: RobotConfigForm
  secretMasked: string
  secretSet: boolean
}

const PLATFORM_TYPES = ['qq_official', 'qq_official_webhook'] as const

const { t, ready, hasBackend } = useBridge()
const router = useRouter()
const { start: startSync } = useSyncRun()

const response = ref<RobotConfigResponse | null>(null)
const drafts = ref<RobotDraft[]>([])
const selectedKey = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const createDialog = ref(false)
const createForm = ref<RobotConfigForm>(emptyRobotForm())
const createError = ref('')
const deleteDialog = ref(false)
const importDialog = ref(false)
const importText = ref('')
const importError = ref('')
const importing = ref(false)

const c2cDialog = ref(false)
const editingC2c = ref<MenuEntry | null>(null)
const c2cParent = ref('')

let draftSeq = 0

const mockMode = computed(() => ready.value && !hasBackend.value)
const selectedDraft = computed(
  () => drafts.value.find((draft) => draft.key === selectedKey.value) ?? null,
)
const selectedForm = computed(
  () => selectedDraft.value?.form ?? emptyRobotForm(),
)
const editable = computed(
  () => selectedDraft.value !== null && hasBackend.value && !mockMode.value && !saving.value,
)
const canSave = computed(
  () =>
    hasBackend.value &&
    !mockMode.value &&
    response.value !== null &&
    !saving.value,
)
const menuLimits = computed(
  () => response.value?.menu_limits ?? { top_level_max: 10, sub_items_max: 5 },
)
const c2cMenuNames = computed(() =>
  selectedForm.value.scenes.c2c.items
    .filter((entry) => entry.type === 'menu' && !entry.parent)
    .map((entry) => entry.name),
)
const c2cTopLevelCount = computed(
  () => selectedForm.value.scenes.c2c.items.filter((entry) => !entry.parent).length,
)
const editingC2cHasChildren = computed(
  () =>
    editingC2c.value?.type === 'menu' &&
    childEntries(
      selectedForm.value.scenes.c2c.items,
      editingC2c.value.name,
    ).length > 0,
)

const platformItems = computed(() =>
  PLATFORM_TYPES.map((value) => ({
    value,
    title: t(
      `pages.dashboard.robots.platformTypeName.${value}`,
      value === 'qq_official' ? 'QQ 官方机器人' : 'QQ 官方机器人 Webhook',
    ),
  })),
)

function createDraft(robot: RobotConfig, index: number): RobotDraft {
  return {
    key: robot.id ? `robot:${robot.id}` : `robot:${index}`,
    form: toRobotForm(robot),
    secretMasked: robot.secret_masked,
    secretSet: robot.secret_set,
  }
}

function applyResponse(next: RobotConfigResponse, preferredAppid = ''): void {
  response.value = next
  const previous =
    preferredAppid || selectedDraft.value?.form.appid.trim() || ''
  drafts.value = next.robots.map(createDraft)
  const matched = previous
    ? drafts.value.find((draft) => draft.form.appid.trim() === previous)
    : undefined
  selectedKey.value = matched?.key ?? drafts.value[0]?.key ?? ''
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    const preferred = selectedDraft.value?.form.appid.trim() ?? ''
    applyResponse(await fetchRobots(), preferred)
  } catch (err) {
    response.value = null
    drafts.value = []
    selectedKey.value = ''
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

function selectRobot(key: string): void {
  selectedKey.value = key
  error.value = ''
}

function openCreate(): void {
  createForm.value = emptyRobotForm()
  createError.value = ''
  createDialog.value = true
}

function confirmCreate(): void {
  const checked = validateRobotForm(
    createForm.value,
    menuLimits.value,
    t,
  )
  if (!checked.ok) {
    createError.value = checked.reason
    return
  }
  const draft: RobotDraft = {
    key: `new:${++draftSeq}`,
    form: {
      ...createForm.value,
      name: createForm.value.name.trim(),
      appid: createForm.value.appid.trim(),
      secret: createForm.value.secret.trim(),
      scenes: {
        c2c: {
          enabled: true,
          items: [],
        },
      },
    },
    secretMasked: '',
    secretSet: Boolean(createForm.value.secret.trim()),
  }
  drafts.value = [...drafts.value, draft]
  selectedKey.value = draft.key
  createDialog.value = false
  notice.value = t(
    'pages.dashboard.robots.created',
    '机器人已加入草稿，保存后才会写入配置。',
  )
}

function removeSelectedRobot(): void {
  const index = drafts.value.findIndex((draft) => draft.key === selectedKey.value)
  if (index < 0) return
  drafts.value = drafts.value.filter((_, current) => current !== index)
  const next = drafts.value[index] ?? drafts.value[index - 1] ?? null
  selectedKey.value = next?.key ?? ''
  deleteDialog.value = false
  notice.value = t(
    'pages.dashboard.robots.removedLocal',
    '已从本地列表移除，保存后才会写入配置。',
  )
}

function robotName(draft: RobotDraft): string {
  return draft.form.name.trim() || t(
    'pages.dashboard.robots.untitledRobot',
    '未命名机器人',
  )
}

function robotMeta(draft: RobotDraft): string {
  return t(
    'pages.dashboard.robots.robotSummary',
    '启用场景 {scenes} 个，菜单条目 {items} 条。',
  )
    .replace('{scenes}', String(robotSceneCount(draft.form)))
    .replace('{items}', String(robotItemCount(draft.form)))
}

function secretHint(draft: RobotDraft): string | undefined {
  if (draft.secretMasked) {
    return t(
      'pages.dashboard.robots.secretSaved',
      '当前密钥：{masked}',
    ).replace('{masked}', draft.secretMasked)
  }
  if (draft.secretSet) {
    return t(
      'pages.dashboard.robots.secretSetHint',
      '已保存 ClientSecret，留空表示沿用原值。',
    )
  }
  return undefined
}

function openAddC2c(parent = ''): void {
  editingC2c.value = null
  c2cParent.value = parent
  c2cDialog.value = true
}

function openEditC2c(entry: MenuEntry): void {
  editingC2c.value = entry
  c2cParent.value = entry.parent
  c2cDialog.value = true
}

function saveC2c(entry: MenuEntry): void {
  const items = selectedForm.value.scenes.c2c.items
  selectedForm.value.scenes.c2c.items = editingC2c.value
    ? replaceEntry(items, editingC2c.value, entry)
    : [...items, entry]
}

function deleteC2c(entry: MenuEntry): void {
  selectedForm.value.scenes.c2c.items = removeEntry(
    selectedForm.value.scenes.c2c.items,
    entry,
  )
}

async function save(options: { sync?: boolean } = {}): Promise<void> {
  if (!hasBackend.value || mockMode.value || !response.value) return

  const robots: RobotConfigPayload[] = []
  const seenAppids = new Set<string>()
  for (const draft of drafts.value) {
    const checked = validateRobotForm(
      draft.form,
      menuLimits.value,
      t,
    )
    if (!checked.ok || !checked.payload) {
      selectedKey.value = draft.key
      error.value = `${robotName(draft)}：${checked.reason}`
      notice.value = ''
      return
    }
    if (seenAppids.has(checked.payload.appid)) {
      selectedKey.value = draft.key
      error.value = t(
        'pages.dashboard.robots.validation.appidDuplicate',
        'AppID 不能重复：{appid}',
      ).replace('{appid}', checked.payload.appid)
      notice.value = ''
      return
    }
    seenAppids.add(checked.payload.appid)
    robots.push(checked.payload)
  }

  saving.value = true
  error.value = ''
  notice.value = ''
  const preferred = selectedForm.value.appid.trim()
  try {
    const next = await saveRobots({
      version: response.value.version,
      robots,
    })
    applyResponse(next, preferred)
    notice.value = t(
      'pages.dashboard.robots.saved',
      '机器人配置已保存。',
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

async function openImport(): Promise<void> {
  importDialog.value = true
  importError.value = ''
  importText.value = ''
  try {
    const legacy = await fetchConfig()
    importText.value = legacy.qq_platforms
      .map((platform) => platform.appid)
      .filter(Boolean)
      .join('\n')
    if (!importText.value) {
      importError.value = t(
        'pages.dashboard.robots.importEmpty',
        '兼容配置里没有可导入的 AppID，请手动填写。',
      )
    }
  } catch (err) {
    importError.value = err instanceof Error ? err.message : String(err)
  }
}

function parseAppids(): string[] {
  const seen = new Set<string>()
  const result: string[] = []
  for (const raw of importText.value.split(/[\s,，]+/)) {
    const appid = raw.trim()
    if (!appid || seen.has(appid)) continue
    seen.add(appid)
    result.push(appid)
  }
  return result
}

async function importLegacy(): Promise<void> {
  if (!response.value || !hasBackend.value) return
  const appids = parseAppids()
  if (!appids.length) {
    importError.value = t(
      'pages.dashboard.robots.importNoAppids',
      '至少填写一个 AppID。',
    )
    return
  }
  importing.value = true
  importError.value = ''
  try {
    const next = await importLegacyRobots(appids, response.value.version)
    applyResponse(next)
    importDialog.value = false
    notice.value = t(
      'pages.dashboard.robots.imported',
      '已从兼容配置导入机器人，请检查后再同步。',
    )
  } catch (err) {
    importError.value = err instanceof Error ? err.message : String(err)
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <v-container fluid class="qc-page qc-robots-page pa-4 pa-md-6">
    <div class="qc-header">
      <div class="qc-header-main">
        <h1 class="qc-title">{{ t('pages.dashboard.robots.title', '机器人') }}</h1>
        <p class="qc-subtitle">
          {{
            t(
              'pages.dashboard.robots.subtitle',
              '每台机器人独立维护自己的私聊菜单，互不覆盖。',
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
          :prepend-icon="mdiImport"
          :disabled="saving || importing"
          @click="openImport"
        >
          {{ t('pages.dashboard.robots.importLegacy', '从兼容配置导入') }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          :prepend-icon="mdiPlus"
          :disabled="saving"
          @click="openCreate"
        >
          {{ t('pages.dashboard.robots.addRobot', '新增机器人') }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          :prepend-icon="mdiContentSave"
          :loading="saving"
          :disabled="!canSave"
          @click="save()"
        >
          {{ t('pages.dashboard.common.save', '保存') }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          :prepend-icon="mdiSync"
          :loading="saving"
          :disabled="!canSave"
          @click="save({ sync: true })"
        >
          {{ t('pages.dashboard.robots.saveAndSync', '保存并同步') }}
        </v-btn>
      </div>
    </div>

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
          'pages.dashboard.robots.mockHint',
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

    <v-dialog v-model="createDialog" max-width="560">
      <v-card class="qc-card">
        <v-card-item class="px-5 pt-5">
          <v-card-title class="text-body-large">
            {{ t('pages.dashboard.robots.addRobot', '新增机器人') }}
          </v-card-title>
          <v-card-subtitle>
            {{
              t(
                'pages.dashboard.robots.createSubtitle',
                '先填写基础凭证，创建后再配置私聊菜单。',
              )
            }}
          </v-card-subtitle>
        </v-card-item>
        <v-card-text class="px-5 pt-3">
          <v-text-field
            v-model="createForm.name"
            data-field="create-name"
            :label="t('pages.dashboard.robots.name', '机器人名称')"
            :maxlength="64"
            :counter="64"
            variant="outlined"
            density="compact"
            class="mb-3"
            hide-details
          />
          <v-text-field
            v-model="createForm.appid"
            data-field="create-appid"
            label="AppID"
            variant="outlined"
            density="compact"
            class="mb-3"
            hide-details
          />
          <v-text-field
            v-model="createForm.secret"
            data-field="create-secret"
            type="password"
            label="ClientSecret"
            variant="outlined"
            density="compact"
            class="mb-3"
            hide-details
          />
          <v-select
            v-model="createForm.platform"
            data-field="create-platform"
            :items="platformItems"
            :label="t('pages.dashboard.robots.platformType', '平台类型')"
            variant="outlined"
            density="compact"
            hide-details
          />
          <v-alert
            v-if="createError"
            type="error"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            {{ createError }}
          </v-alert>
        </v-card-text>
        <v-card-actions class="px-5 pb-5">
          <v-spacer />
          <v-btn variant="text" @click="createDialog = false">
            {{ t('pages.dashboard.common.cancel', '取消') }}
          </v-btn>
          <v-btn color="primary" variant="tonal" @click="confirmCreate">
            {{ t('pages.dashboard.robots.createConfirm', '创建') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="deleteDialog" max-width="480">
      <v-card class="qc-card">
        <v-card-item class="px-5 pt-5">
          <v-card-title class="text-body-large">
            {{ t('pages.dashboard.robots.deleteConfirmTitle', '删除机器人配置？') }}
          </v-card-title>
          <v-card-subtitle>{{ selectedForm.name }}</v-card-subtitle>
        </v-card-item>
        <v-card-text>
          {{
            t(
              'pages.dashboard.robots.deleteConfirmText',
              '删除只移除本地配置，不会清理 QQ 线上已有菜单。保存后才会生效。',
            )
          }}
        </v-card-text>
        <v-card-actions class="px-5 pb-5">
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">
            {{ t('pages.dashboard.common.cancel', '取消') }}
          </v-btn>
          <v-btn color="error" variant="tonal" @click="removeSelectedRobot">
            {{ t('pages.dashboard.robots.deleteConfirm', '确认删除') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="importDialog" max-width="560">
      <v-card class="qc-card">
        <v-card-item class="px-5 pt-5">
          <v-card-title class="text-body-large">
            {{ t('pages.dashboard.robots.importTitle', '从兼容配置导入') }}
          </v-card-title>
          <v-card-subtitle>
            {{
              t(
                'pages.dashboard.robots.importSubtitle',
                '填写要导入的旧版 AppID，每行一个或使用逗号分隔。',
              )
            }}
          </v-card-subtitle>
        </v-card-item>
        <v-card-text class="px-5 pt-3">
          <v-textarea
            v-model="importText"
            data-field="legacy-appids"
            :label="t('pages.dashboard.robots.importAppids', 'AppID 列表')"
            variant="outlined"
            density="compact"
            rows="4"
            hide-details
          />
          <v-alert
            v-if="importError"
            type="error"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            {{ importError }}
          </v-alert>
        </v-card-text>
        <v-card-actions class="px-5 pb-5">
          <v-spacer />
          <v-btn variant="text" @click="importDialog = false">
            {{ t('pages.dashboard.common.cancel', '取消') }}
          </v-btn>
          <v-btn
            color="primary"
            variant="tonal"
            :loading="importing"
            @click="importLegacy"
          >
            {{ t('pages.dashboard.robots.importConfirm', '导入') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-card class="qc-card qc-robots-shell" variant="outlined">
      <section class="qc-robots-pane qc-robot-list" data-pane="list">
        <v-card-item class="px-5 pt-5">
          <v-card-title class="text-body-large">
            {{ t('pages.dashboard.robots.listTitle', '机器人') }}
          </v-card-title>
          <v-card-subtitle>
            {{ t('pages.dashboard.robots.listSubtitle', '选择一台机器人编辑它的场景。') }}
          </v-card-subtitle>
        </v-card-item>
        <v-card-text class="px-5 pb-5 pt-2">
          <div v-if="!drafts.length" class="qc-metric-note">
            {{ t('pages.dashboard.robots.emptyRobots', '还没有机器人，先新增一台。') }}
          </div>
          <v-card
            v-for="draft in drafts"
            :key="draft.key"
            class="qc-config-item mb-3"
            :class="{ 'qc-robot-item--active': draft.key === selectedKey }"
            :variant="draft.key === selectedKey ? 'tonal' : 'flat'"
            :color="draft.key === selectedKey ? 'primary' : undefined"
            role="button"
            tabindex="0"
            @click="selectRobot(draft.key)"
            @keydown.enter.prevent="selectRobot(draft.key)"
            @keydown.space.prevent="selectRobot(draft.key)"
          >
            <div class="d-flex align-center ga-3">
              <v-icon :icon="mdiRobotOutline" size="22" />
              <div class="qc-row-main">
                <div class="font-weight-medium">{{ robotName(draft) }}</div>
                <div class="qc-metric-note">{{ draft.form.appid || '—' }}</div>
                <div class="qc-metric-note">{{ robotMeta(draft) }}</div>
              </div>
            </div>
          </v-card>
        </v-card-text>
      </section>

      <v-divider
        class="qc-robots-divider qc-robots-divider--desktop"
        vertical
        data-field="robots-divider-desktop"
      />
      <v-divider
        class="qc-robots-divider qc-robots-divider--mobile"
        data-field="robots-divider-mobile"
      />

      <section class="qc-robots-pane qc-robot-editor" data-pane="editor">
        <v-card v-if="!selectedDraft" class="qc-card" variant="outlined">
          <v-card-text class="qc-metric-note py-8">
            {{ t('pages.dashboard.robots.editorEmpty', '请选择或新增一台机器人。') }}
          </v-card-text>
        </v-card>

        <template v-else>
          <v-card class="qc-card mb-4" variant="outlined">
            <v-card-item class="px-5 pt-5">
              <v-card-title class="text-body-large">
                {{ t('pages.dashboard.robots.basicTitle', '基础信息') }}
              </v-card-title>
              <v-card-subtitle>
                {{
                  t(
                    'pages.dashboard.robots.basicSubtitle',
                    '名称、AppID 与 ClientSecret 只用于这台机器人。',
                  )
                }}
              </v-card-subtitle>
            </v-card-item>
            <v-card-text class="px-5 pb-5 pt-3">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="selectedForm.name"
                    data-field="robot-name"
                    :disabled="!editable"
                    :label="t('pages.dashboard.robots.name', '机器人名称')"
                    :maxlength="64"
                    :counter="64"
                    variant="outlined"
                    density="compact"
                    hide-details
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="selectedForm.appid"
                    data-field="robot-appid"
                    :disabled="!editable"
                    label="AppID"
                    variant="outlined"
                    density="compact"
                    hide-details
                  />
                </v-col>
                <v-col cols="12" md="8">
                  <v-text-field
                    v-model="selectedForm.secret"
                    data-field="robot-secret"
                    type="password"
                    :disabled="!editable"
                    :placeholder="
                      selectedDraft.secretSet
                        ? t(
                            'pages.dashboard.robots.secretKeep',
                            '留空表示沿用原值',
                          )
                        : ''
                    "
                    :hint="secretHint(selectedDraft)"
                    persistent-hint
                    label="ClientSecret"
                    variant="outlined"
                    density="compact"
                  />
                </v-col>
                <v-col cols="12" md="4">
                  <v-select
                    v-model="selectedForm.platform"
                    data-field="robot-platform"
                    :disabled="!editable"
                    :items="platformItems"
                    :label="t('pages.dashboard.robots.platformType', '平台类型')"
                    variant="outlined"
                    density="compact"
                    hide-details
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <v-card class="qc-card mb-4" variant="outlined">
            <v-card-item class="px-5 pt-5">
              <div class="d-flex align-center ga-3">
                <v-icon :icon="mdiAccountOutline" size="22" />
                <div class="qc-row-main">
                  <v-card-title class="text-body-large">
                    {{ t('pages.dashboard.robots.scene.c2c', '私聊') }}
                  </v-card-title>
                  <v-card-subtitle>
                    {{
                      t(
                        'pages.dashboard.robots.c2c.subtitle',
                        '写入 QQ 全局自定义菜单，支持发送消息、链接、子菜单和开关。',
                      )
                    }}
                  </v-card-subtitle>
                </div>
                <v-spacer />
                <v-switch
                  v-model="selectedForm.scenes.c2c.enabled"
                  data-field="scene-c2c-enabled"
                  color="primary"
                  inset
                  hide-details
                  :disabled="!editable"
                />
              </div>
            </v-card-item>
            <v-card-text class="px-5 pb-5 pt-2">
              <template v-if="selectedForm.scenes.c2c.enabled">
                <div class="d-flex align-center flex-wrap ga-3 mb-3">
                  <span class="qc-metric-note">
                    {{
                      t(
                        'pages.dashboard.robots.c2c.limits',
                        '一级菜单 {top}/{maxTop}，每个子菜单最多 {maxSub} 项。',
                      )
                        .replace('{top}', String(c2cTopLevelCount))
                        .replace('{maxTop}', String(menuLimits.top_level_max))
                        .replace('{maxSub}', String(menuLimits.sub_items_max))
                    }}
                  </span>
                  <v-spacer />
                  <v-btn
                    variant="tonal"
                    color="primary"
                    size="small"
                    :prepend-icon="mdiPlus"
                    :disabled="
                      !editable ||
                      c2cTopLevelCount >= menuLimits.top_level_max
                    "
                    @click="openAddC2c()"
                  >
                    {{ t('pages.dashboard.robots.c2c.add', '添加一级菜单') }}
                  </v-btn>
                </div>
                <MenuTree
                  :entries="selectedForm.scenes.c2c.items"
                  @add-child="openAddC2c"
                  @edit="openEditC2c"
                  @delete="deleteC2c"
                />
              </template>
              <div v-else class="qc-metric-note">
                {{
                  t(
                    'pages.dashboard.robots.c2c.disabled',
                    '私聊场景未启用，插件不会修改 QQ 自定义菜单。',
                  )
                }}
              </div>
            </v-card-text>
          </v-card>

          <v-card class="qc-card mt-4" variant="outlined">
            <v-card-item class="px-5 pt-5">
              <v-card-title class="text-body-large">
                {{ t('pages.dashboard.robots.dangerTitle', '删除机器人配置') }}
              </v-card-title>
            </v-card-item>
            <v-card-text class="px-5 pt-1">
              <v-alert type="warning" variant="tonal" density="compact">
                {{
                  t(
                    'pages.dashboard.robots.dangerText',
                    '删除只移除本地配置，不会自动清理 QQ 线上菜单。',
                  )
                }}
              </v-alert>
            </v-card-text>
            <v-card-actions class="px-5 pb-5">
              <v-btn
                color="error"
                variant="tonal"
                :prepend-icon="mdiTrashCanOutline"
                :disabled="!selectedDraft || saving"
                @click="deleteDialog = true"
              >
                {{ t('pages.dashboard.robots.deleteRobot', '删除机器人配置') }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </template>
      </section>
    </v-card>

    <MenuEntryDialog
      v-model="c2cDialog"
      :entry="editingC2c"
      :parent="c2cParent"
      :menu-names="c2cMenuNames"
      :has-children="editingC2cHasChildren"
      @save="saveC2c"
    />
  </v-container>
</template>
