import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'

export type ThemeType = 'light' | 'dark' | 'auto'
export type ColorMode = 'red-up-green-down' | 'green-up-red-down'

export const useThemeStore = defineStore('theme', () => {
  // 状态
  const theme = ref<ThemeType>('light')
  const systemDark = ref(false)
  const colorMode = ref<ColorMode>('red-up-green-down') // 默认红涨绿跌

  // 计算属性
  const isDark = computed(() => {
    if (theme.value === 'auto') {
      return systemDark.value
    }
    return theme.value === 'dark'
  })

  const currentTheme = computed(() => {
    if (theme.value === 'auto') {
      return systemDark.value ? 'dark' : 'light'
    }
    return theme.value
  })

  // 根据颜色模式获取涨跌颜色类
  const upColorClass = computed(() => colorMode.value === 'red-up-green-down' ? 'text-danger' : 'text-success')
  const downColorClass = computed(() => colorMode.value === 'red-up-green-down' ? 'text-success' : 'text-danger')
  const upBgClass = computed(() => colorMode.value === 'red-up-green-down' ? 'bg-danger' : 'bg-success')
  const downBgClass = computed(() => colorMode.value === 'red-up-green-down' ? 'bg-success' : 'bg-danger')

  // 监听系统主题变化
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

  const updateSystemTheme = () => {
    systemDark.value = mediaQuery.matches
  }

  // 应用主题
  const applyTheme = () => {
    const html = document.documentElement
    const isDarkMode = isDark.value

    if (isDarkMode) {
      html.setAttribute('data-theme', 'dark')
    } else {
      html.removeAttribute('data-theme')
    }

    // 更新 Element Plus 主题
    if (isDarkMode) {
      html.classList.add('dark')
    } else {
      html.classList.remove('dark')
    }
  }

  // 应用颜色模式到 CSS 变量
  const applyColorMode = () => {
    const root = document.documentElement
    if (colorMode.value === 'green-up-red-down') {
      // 绿涨红跌
      root.style.setProperty('--success-color', '#10b981')
      root.style.setProperty('--danger-color', '#ef4444')
      root.style.setProperty('--success-light', 'rgba(16, 185, 129, 0.1)')
      root.style.setProperty('--danger-light', 'rgba(239, 68, 68, 0.1)')
    } else {
      // 红涨绿跌（默认）
      root.style.setProperty('--success-color', '#ef4444')
      root.style.setProperty('--danger-color', '#10b981')
      root.style.setProperty('--success-light', 'rgba(239, 68, 68, 0.1)')
      root.style.setProperty('--danger-light', 'rgba(16, 185, 129, 0.1)')
    }
  }

  // 设置主题
  const setTheme = (newTheme: ThemeType) => {
    theme.value = newTheme
    saveTheme()
    applyTheme()
  }

  // 切换主题
  const toggleTheme = () => {
    const themes: ThemeType[] = ['light', 'dark', 'auto']
    const currentIndex = themes.indexOf(theme.value)
    const nextIndex = (currentIndex + 1) % themes.length
    const nextTheme = themes[nextIndex]
    if (nextTheme) {
      setTheme(nextTheme)
    }
  }

  // 设置颜色模式
  const setColorMode = (mode: ColorMode) => {
    colorMode.value = mode
    applyColorMode()
    saveTheme()
  }

  // 保存到 localStorage
  const saveTheme = () => {
    try {
      localStorage.setItem('fund-tracker-theme', theme.value)
      localStorage.setItem('fund-tracker-color-mode', colorMode.value)
    } catch (e) {
      console.warn('保存主题设置失败:', e)
    }
  }

  // 从 localStorage 加载
  const loadTheme = () => {
    try {
      const saved = localStorage.getItem('fund-tracker-theme')
      if (saved && ['light', 'dark', 'auto'].includes(saved)) {
        theme.value = saved as ThemeType
      }
      const savedColorMode = localStorage.getItem('fund-tracker-color-mode') as ColorMode
      if (savedColorMode && ['red-up-green-down', 'green-up-red-down'].includes(savedColorMode)) {
        colorMode.value = savedColorMode
      }
    } catch (e) {
      console.warn('加载主题设置失败:', e)
    }
  }

  // 初始化
  const init = () => {
    // 加载保存的主题
    loadTheme()

    // 监听系统主题
    updateSystemTheme()
    mediaQuery.addEventListener('change', updateSystemTheme)

    // 应用主题
    applyTheme()
    applyColorMode()

    // 监听主题变化
    watch([theme, systemDark], applyTheme, { immediate: true })

    return () => {
      mediaQuery.removeEventListener('change', updateSystemTheme)
    }
  }

  return {
    theme,
    isDark,
    currentTheme,
    colorMode,
    upColorClass,
    downColorClass,
    upBgClass,
    downBgClass,
    setTheme,
    toggleTheme,
    setColorMode,
    init
  }
})
