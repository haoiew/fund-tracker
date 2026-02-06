import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Layout',
    component: () => import('@/components/Layout/MainLayout.vue'),
    redirect: '/home',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('@/views/Home/HomeView.vue'),
        meta: { title: '首页', icon: 'HomeFilled' }
      },
      {
        path: 'screen',
        name: 'Screen',
        component: () => import('@/views/Screen/ScreenView.vue'),
        meta: { title: '基金筛选', icon: 'Filter' }
      },
      {
        path: 'compare',
        name: 'Compare',
        component: () => import('@/views/Compare/CompareView.vue'),
        meta: { title: '基金对比', icon: 'TrendCharts' }
      },
      {
        path: 'portfolio',
        name: 'Portfolio',
        component: () => import('@/views/Portfolio/PortfolioView.vue'),
        meta: { title: '持仓管理', icon: 'WalletFilled' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings/SettingsView.vue'),
        meta: { title: '设置', icon: 'Setting' }
      },
      {
        path: 'about',
        name: 'About',
        component: () => import('@/views/About/AboutView.vue'),
        meta: { title: '关于', icon: 'InfoFilled' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/Error/NotFoundView.vue'),
    meta: { title: '页面未找到' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - Fund Tracker`
  } else {
    document.title = 'Fund Tracker'
  }

  console.log(`[Router] 路由切换: ${from.path} -> ${to.path}`)
  next()
})

// 路由错误处理
router.onError((error) => {
  console.error('[Router] 路由错误:', error)
})

export default router
