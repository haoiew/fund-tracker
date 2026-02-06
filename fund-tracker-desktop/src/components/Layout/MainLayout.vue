<template>
  <div class="app-container">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" class="logo-svg">
              <defs>
                <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style="stop-color:#6366f1"/>
                  <stop offset="50%" style="stop-color:#8b5cf6"/>
                  <stop offset="100%" style="stop-color:#a855f7"/>
                </linearGradient>
              </defs>
              <rect x="4" y="8" width="40" height="32" rx="6" fill="url(#logoGradient)"/>
              <path d="M14 28L20 22L26 26L34 18" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
              <circle cx="34" cy="18" r="2" fill="white"/>
              <path d="M12 14H18" stroke="white" stroke-width="2" stroke-linecap="round" opacity="0.6"/>
            </svg>
          </div>
          <div class="logo-text-container">
            <span class="logo-text">基金跟踪器</span>
            <span class="logo-subtitle">Fund Tracker</span>
          </div>
        </div>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="route in menuRoutes"
          :key="route.path"
          :to="`/${route.path}`"
          class="nav-item"
          :class="{ active: isActiveRoute(route.path) }"
          @click="handleNavClick(route.path)"
        >
          <div class="nav-icon">
            <el-icon size="18">
              <component :is="route.meta?.icon" />
            </el-icon>
          </div>
          <span class="nav-text">{{ route.meta?.title }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="refresh-btn" @click="refreshAll">
          <el-icon size="16" :class="{ spinning: isRefreshing }"><Refresh /></el-icon>
          <span>刷新数据</span>
        </div>
        <div class="version">v2.0.0</div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 顶部栏 -->
      <header class="top-header">
        <div class="header-left">
          <h1 class="page-title">{{ pageTitle }}</h1>
          <p class="page-subtitle">{{ pageSubtitle }}</p>
        </div>
        <div class="header-right">
          <div class="header-actions">
            <el-tooltip content="通知" placement="bottom">
              <div class="action-btn">
                <el-icon size="18"><Bell /></el-icon>
                <span class="badge" v-if="notificationCount > 0">{{ notificationCount }}</span>
              </div>
            </el-tooltip>
            <el-tooltip :content="$t('settings.theme')" placement="bottom">
              <div class="action-btn" @click="toggleTheme">
                <el-icon size="18"><Sunny v-if="themeStore.isDark" /><Moon v-else /></el-icon>
              </div>
            </el-tooltip>
          </div>
        </div>
      </header>

      <!-- 页面内容 -->
      <div class="page-wrapper">
        <router-view v-slot="{ Component, route }">
          <transition name="page" mode="out-in">
            <keep-alive :include="cachedViews">
              <component :is="Component" :key="route.fullPath" />
            </keep-alive>
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Refresh, Bell, Moon, Sunny } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/themeStore'
import { dataManager } from '@/stores/dataManager'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()

const isRefreshing = ref(false)
const notificationCount = ref(0)
const activeRoutePath = ref(route.path)

// 需要缓存的页面组件名称列表
const cachedViews = ref([
  'HomeView',
  'ScreenView',
  'CompareView',
  'PortfolioView',
  'SettingsView',
  'AboutView'
])

// 监听路由变化
watch(() => route.path, (newPath) => {
  activeRoutePath.value = newPath
}, { immediate: true })

// 菜单路由
const menuRoutes = computed(() => {
  const layoutRoute = router.getRoutes().find(r => r.name === 'Layout')
  const children = layoutRoute?.children || []
  // 过滤掉 OCR 路由
  return children.filter(r => r.path !== 'ocr')
})

// 判断路由是否激活
const isActiveRoute = (path: string) => {
  const fullPath = `/${path}`
  return activeRoutePath.value === fullPath
}

// 处理导航点击
const handleNavClick = (path: string) => {
  const targetPath = `/${path}`
  if (route.path !== targetPath) {
    router.push(targetPath)
  }
}

// 页面标题
const pageTitle = computed(() => {
  const currentRoute = menuRoutes.value.find(r => `/${r.path}` === route.path)
  return currentRoute?.meta?.title || '首页'
})

const pageSubtitle = computed(() => {
  const subtitles: Record<string, string> = {
    'home': '实时追踪您的基金动态',
    'screen': '筛选连续涨跌的基金',
    'compare': '对比多只基金表现',
    'portfolio': '管理您的投资组合',
    'settings': '个性化您的应用',
    'about': '了解基金跟踪器更多信息'
  }
  const currentRoute = menuRoutes.value.find(r => `/${r.path}` === route.path)
  return subtitles[currentRoute?.path as string] || ''
})

// 刷新所有数据 - 使用 DataManager 统一刷新
const refreshAll = async () => {
  if (isRefreshing.value) return

  isRefreshing.value = true
  try {
    // 使用 DataManager 统一刷新所有数据
    await dataManager.refreshAll()
    ElMessage.success({
      message: '数据已更新',
      duration: 2000,
      plain: true
    })
  } catch {
    ElMessage.error('刷新失败')
  } finally {
    setTimeout(() => {
      isRefreshing.value = false
    }, 500)
  }
}

// 切换主题
const toggleTheme = () => {
  themeStore.toggleTheme()
}

onMounted(() => {
  // 初始化主题
  themeStore.init()
  // 使用 DataManager 统一初始化所有数据
  dataManager.initialize()
})
</script>

<style scoped lang="scss">
.app-container {
  display: flex;
  height: 100vh;
  background: var(--bg-page);
  font-family: var(--font-family);
}

// 侧边栏
.sidebar {
  width: 220px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-base);
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 100;
}

.sidebar-header {
  padding: 20px 16px;
  border-bottom: 1px solid var(--border-light);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
  overflow: hidden;
  
  .logo-svg {
    width: 100%;
    height: 100%;
  }
}

.logo-text-container {
  display: flex;
  flex-direction: column;
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.3px;
  line-height: 1.2;
}

.logo-subtitle {
  font-size: 10px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-top: 2px;
}

// 导航菜单
.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-base);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition-base);
  position: relative;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.active {
    background: var(--primary-color);
    color: white;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
  }
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.1);
}

.nav-text {
  font-size: 14px;
  font-weight: 500;
}

// 侧边栏底部
.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--border-light);
}

.refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  background: var(--bg-base);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-base);
  color: var(--text-regular);
  cursor: pointer;
  transition: all var(--transition-base);
  margin-bottom: 8px;
  font-size: 13px;

  &:hover {
    border-color: var(--primary-color);
    color: var(--primary-color);
  }

  .el-icon {
    transition: transform 0.5s ease;

    &.spinning {
      animation: spin 1s linear infinite;
    }
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.version {
  text-align: center;
  font-size: 11px;
  color: var(--text-placeholder);
}

// 主内容区
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

// 顶部栏
.top-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--bg-base);
  border-bottom: 1px solid var(--border-light);
}

.header-left {
  .page-title {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 2px 0;
  }

  .page-subtitle {
    font-size: 12px;
    color: var(--text-secondary);
    margin: 0;
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  position: relative;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-page);
  border-radius: var(--radius-base);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-base);

  &:hover {
    background: var(--primary-light);
    color: var(--primary-color);
  }

  .badge {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 16px;
    height: 16px;
    background: var(--danger-color);
    color: white;
    font-size: 10px;
    font-weight: 600;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

// 页面内容
.page-wrapper {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
  background: var(--bg-page);
}

// 页面过渡动画
.page-enter-active,
.page-leave-active {
  transition: all 0.2s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>
