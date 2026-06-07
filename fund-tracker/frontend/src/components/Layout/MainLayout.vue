<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="sidebar-brand">
        <div class="brand-mark" aria-hidden="true">
          <el-icon size="26"><TrendCharts /></el-icon>
        </div>
        <div class="brand-copy">
          <span class="brand-name">{{ appName }}</span>
          <span class="brand-subtitle">{{ appSubtitle }}</span>
        </div>
      </div>

      <nav class="sidebar-nav" aria-label="主导航">
        <router-link
          v-for="item in menuRoutes"
          :key="item.path"
          :to="`/${item.path}`"
          class="nav-item"
          :class="{ active: isActiveRoute(item.path) }"
        >
          <span class="nav-icon">
            <el-icon size="18">
              <component :is="item.meta?.icon" />
            </el-icon>
          </span>
          <span class="nav-copy">
            <span class="nav-title">{{ item.meta?.title }}</span>
            <span class="nav-subtitle">{{ getRouteSubtitle(item.path) }}</span>
          </span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="sidebar-actions">
          <el-tooltip content="刷新全部数据" placement="right">
            <button class="icon-button" type="button" aria-label="刷新全部数据" :disabled="isRefreshing" @click="refreshAll">
              <el-icon size="16" :class="{ spinning: isRefreshing }"><Refresh /></el-icon>
            </button>
          </el-tooltip>
          <el-tooltip :content="$t('settings.theme')" placement="right">
            <button class="icon-button" type="button" aria-label="切换主题" @click="toggleTheme">
              <el-icon size="16"><Sunny v-if="themeStore.isDark" /><Moon v-else /></el-icon>
            </button>
          </el-tooltip>
        </div>

        <div class="version-line">{{ appVersion }}</div>
      </div>
    </aside>

    <main class="app-main">
      <header class="topbar">
        <div class="topbar-context">
          <span class="topbar-product">本地数据工作台</span>
          <span class="topbar-separator"></span>
          <span class="topbar-subtitle">多源行情 · 本地缓存 · 轻量桌面</span>
        </div>

        <div class="topbar-actions">
          <div class="status-chip" :class="syncStatus.className">
            <span class="status-dot" :class="syncStatus.className"></span>
            <span class="status-label">{{ syncStatus.label }}</span>
          </div>

          <el-tooltip content="刷新全部数据" placement="bottom">
            <button class="icon-button" type="button" aria-label="刷新全部数据" :disabled="isRefreshing" @click="refreshAll">
              <el-icon size="18" :class="{ spinning: isRefreshing }"><Refresh /></el-icon>
            </button>
          </el-tooltip>

          <el-tooltip :content="$t('settings.theme')" placement="bottom">
            <button class="icon-button" type="button" aria-label="切换主题" @click="toggleTheme">
              <el-icon size="18"><Sunny v-if="themeStore.isDark" /><Moon v-else /></el-icon>
            </button>
          </el-tooltip>
        </div>
      </header>

      <section class="content-shell">
        <router-view v-slot="{ Component, route }">
          <transition name="page" mode="out-in">
            <keep-alive :include="cachedViews">
              <component :is="Component" :key="route.fullPath" />
            </keep-alive>
          </transition>
        </router-view>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'MainLayout'
})

import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Moon, Refresh, Sunny, TrendCharts } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/themeStore'
import { dataManager } from '@/stores/dataManager'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()
const managerState = dataManager.getState()

const isRefreshing = ref(false)

const cachedViews = ref([
  'HomeView',
  'ScreenView',
  'CompareView',
  'PortfolioView',
  'SettingsView',
  'AboutView'
])

const menuRoutes = computed(() => {
  const layoutRoute = router.getRoutes().find((item) => item.name === 'Layout')
  return layoutRoute?.children || []
})

const appName = '基金跟踪器'
const appSubtitle = 'Fund Tracker'
const appVersion = 'v2.0.0'

const routeSubtitleMap: Record<string, string> = {
  home: '实时追踪与概览',
  screen: '筛选连续涨跌基金',
  compare: '多基金表现对照',
  portfolio: '持仓与收益管理',
  settings: '界面与数据配置',
  about: '版本与项目说明'
}

const getRouteSubtitle = (path: string) => routeSubtitleMap[path] || ''

const isActiveRoute = (path: string) => route.path === `/${path}`

const syncStatus = computed(() => {
  const hasError = Boolean(managerState.fundListError || managerState.realtimeError || managerState.portfolioError)
  const isLoading = isRefreshing.value || managerState.fundListLoading || managerState.realtimeLoading || managerState.portfolioLoading

  if (hasError) {
    return {
      label: '数据异常',
      className: 'is-error'
    }
  }

  if (isLoading) {
    return {
      label: '同步中',
      className: 'is-loading'
    }
  }

  return {
    label: '数据就绪',
    className: 'is-ready'
  }
})

const refreshAll = async () => {
  if (isRefreshing.value) return

  isRefreshing.value = true
  try {
    await dataManager.refreshAll()
    ElMessage.success({
      message: '数据已更新',
      duration: 1800,
      plain: true
    })
  } catch {
    ElMessage.error('刷新失败')
  } finally {
    isRefreshing.value = false
  }
}

const toggleTheme = () => {
  themeStore.toggleTheme()
}

watch(
  () => route.path,
  () => {},
  { immediate: true }
)

onMounted(() => {
  themeStore.init()
  dataManager.initialize()
})
</script>

<style scoped lang="scss">
.app-shell {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
  background: var(--bg-app-shell);
  color: var(--text-primary);
}

.app-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 20px 18px 18px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-light);
  backdrop-filter: blur(18px);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 10px 18px;
}

.brand-mark {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-base);
  background: var(--icon-surface-primary);
  border: 1px solid var(--icon-border-primary);
  color: var(--primary-color);
  box-shadow: var(--shadow-light);
}

.brand-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.brand-name {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0;
  white-space: nowrap;
}

.brand-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  letter-spacing: 0;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 6px 0;
  flex: 1;
}

.nav-item {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  min-height: 58px;
  padding: 10px 12px;
  border-radius: var(--radius-base);
  color: var(--text-secondary);
  border: 1px solid transparent;
  transition: background-color var(--transition-base), border-color var(--transition-base), color var(--transition-base), transform var(--transition-base);
}

.nav-item:hover {
  background: var(--bg-hover);
  border-color: var(--border-light);
  color: var(--text-primary);
  transform: translateX(2px);
}

.nav-item.active {
  background: var(--bg-sidebar-active);
  border-color: rgba(37, 99, 235, 0.18);
  color: var(--text-primary);
  box-shadow: var(--shadow-light);
}

.nav-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-base);
  background: var(--bg-base);
  color: var(--primary-color);
}

.nav-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.nav-title {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.2;
}

.nav-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.2;
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 10px 4px;
}

.sidebar-actions {
  display: flex;
  gap: 10px;
}

.icon-button {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-base);
  background: var(--bg-base);
  color: var(--text-primary);
  cursor: pointer;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast), background-color var(--transition-fast);
}

.icon-button:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(37, 99, 235, 0.28);
  box-shadow: var(--shadow-light);
}

.icon-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

.version-line {
  font-size: 12px;
  color: var(--text-placeholder);
  text-align: center;
}

.app-main {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 14px 18px 18px 0;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 48px;
  padding: 0 18px 12px 22px;
}

.topbar-context {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.topbar-product {
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.topbar-product {
  color: var(--text-secondary);
}

.topbar-separator {
  width: 1px;
  height: 14px;
  background: var(--border-base);
}

.topbar-subtitle {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: var(--text-secondary);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 14px;
  border-radius: var(--radius-base);
  background: var(--bg-base);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-light);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: var(--status-ready-color);
  box-shadow: 0 0 0 4px var(--status-ready-light);
}

.status-dot.is-loading {
  background: var(--status-warning-color);
  box-shadow: 0 0 0 4px var(--status-warning-light);
}

.status-dot.is-error {
  background: var(--status-error-color);
  box-shadow: 0 0 0 4px var(--status-error-light);
}

.status-chip.is-error {
  border-color: var(--status-error-light);
}

.status-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.content-shell {
  min-width: 0;
  min-height: 0;
  flex: 1;
  padding: 0 22px 22px;
  overflow: auto;
}

.page-enter-active,
.page-leave-active {
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 1280px) {
  .app-shell {
    grid-template-columns: 88px minmax(0, 1fr);
  }

  .app-sidebar {
    padding-inline: 12px;
  }

  .brand-copy,
  .nav-copy,
  .version-line {
    display: none;
  }

  .sidebar-brand,
  .sidebar-footer {
    justify-content: center;
  }

  .nav-item {
    grid-template-columns: 1fr;
    justify-items: center;
    padding: 10px 8px;
  }

  .nav-icon {
    margin: 0;
  }

  .app-main {
    padding-left: 0;
  }
}

@media (max-width: 960px) {
  .app-shell {
    grid-template-columns: 1fr;
    grid-template-rows: auto minmax(0, 1fr);
  }

  .app-sidebar {
    position: relative;
    height: auto;
    flex-direction: row;
    align-items: center;
    gap: 14px;
    padding: 14px 16px;
  }

  .sidebar-brand {
    padding: 0;
  }

  .sidebar-nav {
    flex-direction: row;
    overflow-x: auto;
    padding: 0;
    gap: 8px;
  }

  .nav-item {
    min-width: 168px;
    flex: 0 0 auto;
  }

  .sidebar-footer {
    display: none;
  }

  .app-main {
    padding: 0 12px 12px;
  }

  .topbar {
    padding-inline: 6px;
    flex-direction: column;
    align-items: stretch;
  }

  .content-shell {
    padding: 0 6px 12px;
  }
}
</style>
