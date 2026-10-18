/**
 * AppShell 的侧边栏与标题状态。
 *
 * 抽成 composable 让「窄屏临时抽屉 / 宽屏 rail」两套交互脱离模板就能被驱动，
 * 模板只留绑定（见同目录 AppShell.test.ts）。
 */

import { computed, ref, watch } from 'vue'
import { mdiClose, mdiMenuClose, mdiMenuOpen } from '@mdi/js'
import { useDisplay } from 'vuetify'
import { useBridge } from '../composables/useBridge'

/**
 * 宿主在某些 AstrBot 版本会把视图名直接当成 pageTitle 传入（常见值是
 * `dashboard`）。它不是本地化标题，不能覆盖插件自己的 i18n。
 */
export function resolvePageTitle(
  pageTitle: string | undefined,
  displayName: string | undefined,
  fallback: string,
): string {
  const candidates = [pageTitle, displayName]
    .map((value) => value?.trim() ?? '')
    .filter(Boolean)
  const meaningful = candidates.find(
    (value) =>
      !['dashboard', 'pages.dashboard', 'views.dashboard'].includes(
        value.toLowerCase(),
      ),
  )
  return meaningful ?? fallback
}

export function useAppShell() {
  const { mobile } = useDisplay()
  const { context, isDark, t } = useBridge()

  // 窄屏：抽屉是临时抽屉，开关的是它；宽屏：抽屉常驻，开关的是折叠 (rail)
  const drawer = ref(!mobile.value)
  const rail = ref(false)

  watch(mobile, (isMobile) => {
    drawer.value = !isMobile
  })

  const railActive = computed(() => !mobile.value && rail.value)

  function toggleSidebar(): void {
    if (mobile.value) {
      drawer.value = !drawer.value
      return
    }
    rail.value = !rail.value
  }

  function onDrawerUpdate(value: boolean): void {
    // 宽屏时抽屉常驻，只由我们自己的开关控制
    if (mobile.value) {
      drawer.value = value
    }
  }

  // 侧边栏 brand 行里的按钮：宽屏折叠/展开，窄屏关闭抽屉
  const toggleIcon = computed(() => {
    if (mobile.value) return mdiClose
    return railActive.value ? mdiMenuOpen : mdiMenuClose
  })

  const toggleLabel = computed(() => {
    if (mobile.value) {
      return t('pages.dashboard.nav.closeDrawer', '关闭侧边栏')
    }
    return railActive.value
      ? t('pages.dashboard.nav.expand', '展开侧边栏')
      : t('pages.dashboard.nav.collapse', '收起侧边栏')
  })

  const title = computed(
    () => {
      const fallback = t('pages.dashboard.title', '自定义菜单')
      return resolvePageTitle(
        context.value?.pageTitle,
        context.value?.displayName,
        fallback,
      )
    },
  )

  return {
    mobile,
    isDark,
    t,
    drawer,
    railActive,
    toggleSidebar,
    onDrawerUpdate,
    toggleIcon,
    toggleLabel,
    title,
  }
}
