<template>
  <div class="settings-view workbench-page">
    <section class="page-toolbar">
      <div class="page-toolbar__main">
        <span class="page-toolbar__icon">
          <el-icon><Setting /></el-icon>
        </span>
        <div class="page-toolbar__copy">
          <h2 class="page-toolbar__title">应用偏好与数据配置</h2>
          <p class="page-toolbar__meta">本地保存 · {{ activeSectionMeta.title }} · {{ activeSectionMeta.summary }}</p>
        </div>
      </div>
      <div class="page-toolbar__actions">
        <el-button type="primary" @click="saveSettings">{{ $t('common.save') }}</el-button>
        <el-button @click="resetSettings">{{ $t('common.reset') }}</el-button>
      </div>
    </section>

    <section class="settings-workbench surface-panel">
      <aside class="settings-nav" aria-label="设置分类">
        <button
          v-for="item in settingsSections"
          :key="item.key"
          type="button"
          class="settings-nav-item"
          :class="{ active: activeSection === item.key }"
          @click="activeSection = item.key"
        >
          <span class="settings-nav-icon">
            <el-icon><component :is="item.icon" /></el-icon>
          </span>
          <span class="settings-nav-copy">
            <span>{{ item.title }}</span>
            <small>{{ item.summary }}</small>
          </span>
        </button>
      </aside>

      <div class="settings-detail">
        <header class="settings-detail-header">
          <div>
            <h3>{{ activeSectionMeta.title }}</h3>
            <p>{{ activeSectionMeta.description }}</p>
          </div>
        </header>

        <el-form label-position="top" class="settings-form">
          <div v-if="activeSection === 'appearance'" class="settings-grid">
            <div class="setting-card">
              <div class="setting-card__header">
                <span>语言</span>
                <small>界面文案显示语言</small>
              </div>
              <el-radio-group v-model="settings.language" @change="changeLanguage">
                <el-radio-button value="zh-CN">中文</el-radio-button>
                <el-radio-button value="en-US">English</el-radio-button>
              </el-radio-group>
            </div>

            <div class="setting-card">
              <div class="setting-card__header">
                <span>主题</span>
                <small>手动指定或跟随系统</small>
              </div>
              <el-radio-group v-model="themeStore.theme" @change="handleThemeChange">
                <el-radio-button value="light">{{ $t('settings.light') }}</el-radio-button>
                <el-radio-button value="dark">{{ $t('settings.dark') }}</el-radio-button>
                <el-radio-button value="auto">{{ $t('settings.auto') }}</el-radio-button>
              </el-radio-group>
            </div>

            <div class="setting-card is-wide">
              <div class="setting-card__header">
                <span>涨跌颜色</span>
                <small>匹配你熟悉的市场颜色习惯</small>
              </div>
              <el-radio-group v-model="settings.colorMode" @change="handleColorModeChange">
                <el-radio-button value="red-up-green-down">
                  <span class="color-preview red-up">红涨绿跌</span>
                </el-radio-button>
                <el-radio-button value="green-up-red-down">
                  <span class="color-preview green-up">绿涨红跌</span>
                </el-radio-button>
              </el-radio-group>
            </div>
          </div>

          <div v-else-if="activeSection === 'data'" class="settings-stack">
            <div class="setting-row">
              <div>
                <span>{{ $t('settings.apiUrl') }}</span>
                <small>前端请求 FastAPI 服务的基础地址</small>
              </div>
              <el-input v-model="settings.apiUrl" placeholder="http://127.0.0.1:8001/api/v1" />
            </div>

            <div class="setting-row">
              <div>
                <span>{{ $t('settings.autoRefresh') }}</span>
                <small>开启后按固定间隔刷新行情与持仓</small>
              </div>
              <el-switch v-model="settings.autoRefresh" />
            </div>

            <div class="setting-row" v-if="settings.autoRefresh">
              <div>
                <span>{{ $t('settings.refreshInterval') }}</span>
                <small>当前间隔 {{ settings.refreshInterval }}{{ $t('common.second') }}</small>
              </div>
              <div class="slider-control">
                <el-slider v-model="settings.refreshInterval" :min="10" :max="300" :step="10" show-stops />
              </div>
            </div>

            <div class="setting-row">
              <div>
                <span>天数统计口径</span>
                <small>影响“N天内累计涨跌幅”筛选方式</small>
              </div>
              <el-radio-group v-model="settings.dayCountMode">
                <el-radio-button value="trading">交易日</el-radio-button>
                <el-radio-button value="calendar">自然日</el-radio-button>
              </el-radio-group>
            </div>
          </div>

          <div v-else-if="activeSection === 'ai'" class="settings-stack">
            <div class="setting-row">
              <div>
                <span>模型名称</span>
                <small>用于持仓截图识别的模型标识</small>
              </div>
              <el-input v-model="settings.aiModel" placeholder="例如 gpt-4o、mimo-v2-pro" />
            </div>

            <div class="setting-row">
              <div>
                <span>Base URL</span>
                <small>兼容 OpenAI 接口格式的服务地址</small>
              </div>
              <el-input v-model="settings.aiBaseUrl" placeholder="https://api.example.com/v1" />
            </div>

            <div class="setting-row">
              <div>
                <span>API Key</span>
                <small>仅保存在本地浏览器存储中</small>
              </div>
              <el-input v-model="settings.aiApiKey" type="password" show-password placeholder="sk-..." />
            </div>

            <div class="setting-row is-vertical">
              <div>
                <span>识别提示词</span>
                <small>约束截图识别输出 JSON 结构</small>
              </div>
              <el-input
                v-model="settings.aiPrompt"
                type="textarea"
                :rows="8"
                placeholder="用于识别持仓截图的提示词"
              />
            </div>
          </div>

          <div v-else class="settings-grid">
            <div class="setting-card">
              <div class="setting-card__header">
                <span>{{ $t('settings.version') }}</span>
                <small>当前桌面应用版本</small>
              </div>
              <strong>v2.0.0</strong>
            </div>
            <div class="setting-card">
              <div class="setting-card__header">
                <span>存储位置</span>
                <small>设置和 AI 配置</small>
              </div>
              <strong>localStorage</strong>
            </div>
          </div>
        </el-form>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'SettingsView'
})

import { computed, reactive, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useThemeStore, type ThemeType } from '@/stores/themeStore'
import { Brush, Coin, InfoFilled, MagicStick, Setting } from '@element-plus/icons-vue'
import {
  DEFAULT_APP_SETTINGS,
  loadAppSettings,
  saveAppSettings,
  type AppSettings
} from '@/platform/appSettings'

const { locale, t } = useI18n()
const themeStore = useThemeStore()

type SettingsSectionKey = 'appearance' | 'data' | 'ai' | 'about'

const activeSection = ref<SettingsSectionKey>('appearance')

const settingsSections = [
  {
    key: 'appearance',
    title: '外观',
    summary: '主题与语言',
    description: '控制界面语言、主题模式和涨跌颜色表达。',
    icon: Brush
  },
  {
    key: 'data',
    title: '数据',
    summary: '接口与刷新',
    description: '配置接口地址、刷新策略和筛选统计口径。',
    icon: Coin
  },
  {
    key: 'ai',
    title: 'AI 识别',
    summary: '截图导入',
    description: '配置持仓截图识别导入所需的模型、密钥和提示词。',
    icon: MagicStick
  },
  {
    key: 'about',
    title: '应用信息',
    summary: '版本与存储',
    description: '查看当前版本和本地配置存储方式。',
    icon: InfoFilled
  }
] as const

const activeSectionMeta = computed(() => settingsSections.find(item => item.key === activeSection.value) ?? settingsSections[0])

const settings = reactive<AppSettings>({ ...DEFAULT_APP_SETTINGS })

const changeLanguage = (lang: string) => {
  locale.value = lang
  localStorage.setItem('fund-tracker-language', lang)
  ElMessage.success(lang === 'zh-CN' ? '语言已切换为中文' : 'Language switched to English')
}

const handleThemeChange = (theme: ThemeType) => {
  themeStore.setTheme(theme)
  ElMessage.success(t('settings.themeChanged'))
}

const handleColorModeChange = (colorMode: string) => {
  localStorage.setItem('fund-tracker-color-mode', colorMode)
  ElMessage.success('颜色模式已更新')
}

const saveSettings = () => {
  saveAppSettings({ ...settings })
  localStorage.setItem('fund-tracker-language', settings.language)
  localStorage.setItem('fund-tracker-color-mode', settings.colorMode)
  ElMessage.success(t('settings.saved'))
}

const resetSettings = () => {
  Object.assign(settings, DEFAULT_APP_SETTINGS)
  themeStore.setTheme('light')
  changeLanguage('zh-CN')
  localStorage.setItem('fund-tracker-color-mode', 'red-up-green-down')
  ElMessage.info(t('settings.reset'))
}

// 加载设置
onMounted(() => {
  Object.assign(settings, loadAppSettings())

  // 加载语言设置
  const savedLang = localStorage.getItem('fund-tracker-language')
  if (savedLang) {
    settings.language = savedLang
    locale.value = savedLang
  }

  // 加载颜色模式设置
  const savedColorMode = localStorage.getItem('fund-tracker-color-mode')
  if (savedColorMode === 'red-up-green-down' || savedColorMode === 'green-up-red-down') {
    settings.colorMode = savedColorMode
  }
})
</script>

<style scoped lang="scss">
.settings-view {
  .settings-workbench {
    display: grid;
    grid-template-columns: 260px minmax(0, 1fr);
    min-height: 540px;
    overflow: hidden;
  }

  .settings-nav {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 14px;
    border-right: 1px solid var(--border-light);
    background: var(--bg-hover);
  }

  .settings-nav-item {
    width: 100%;
    display: grid;
    grid-template-columns: 36px minmax(0, 1fr);
    align-items: center;
    gap: 10px;
    padding: 10px;
    border: 1px solid transparent;
    border-radius: var(--radius-base);
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    text-align: left;
    transition: background-color var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast);

    &:hover,
    &.active {
      background: var(--bg-card);
      border-color: var(--border-light);
      color: var(--text-primary);
      box-shadow: var(--shadow-light);
    }
  }

  .settings-nav-icon {
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    border-radius: var(--radius-base);
    background: var(--icon-surface);
    color: var(--primary-color);
  }

  .settings-nav-copy {
    display: flex;
    flex-direction: column;
    min-width: 0;

    span {
      color: inherit;
      font-size: 14px;
      font-weight: 800;
    }

    small {
      margin-top: 2px;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 600;
    }
  }

  .settings-detail {
    min-width: 0;
    padding: 18px 20px;
  }

  .settings-detail-header {
    margin-bottom: 18px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border-light);

    h3 {
      margin: 0;
      color: var(--text-primary);
      font-size: 18px;
      font-weight: 800;
    }

    p {
      margin-top: 4px;
      color: var(--text-secondary);
      font-size: 13px;
    }
  }

  .settings-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .settings-stack {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .setting-card,
  .setting-row {
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background: var(--bg-card);
  }

  .setting-card.is-wide {
    grid-column: 1 / -1;
  }

  .setting-card__header,
  .setting-row > div:first-child {
    margin-bottom: 12px;

    span {
      display: block;
      color: var(--text-primary);
      font-size: 14px;
      font-weight: 800;
    }

    small {
      display: block;
      margin-top: 3px;
      color: var(--text-secondary);
      font-size: 12px;
    }
  }

  .setting-row {
    display: grid;
    grid-template-columns: minmax(210px, 0.38fr) minmax(0, 1fr);
    align-items: center;
    gap: 18px;

    > div:first-child {
      margin-bottom: 0;
    }
  }

  .setting-row.is-vertical {
    display: block;
  }

  .slider-control {
    min-width: 0;
    padding-inline: 8px;
  }

  .form-tip {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
  }

  :deep(.el-form-item) {
    margin-bottom: 0;
  }

  :deep(.el-form-item:last-child) {
    margin-bottom: 0;
  }

  .color-preview {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;

    &.red-up::before {
      content: '';
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: #f56c6c;
    }

    &.green-up::before {
      content: '';
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: #67c23a;
    }
  }

  @media (max-width: 920px) {
    .settings-workbench {
      grid-template-columns: 1fr;
    }

    .settings-nav {
      flex-direction: row;
      overflow-x: auto;
      border-right: 0;
      border-bottom: 1px solid var(--border-light);
    }

    .settings-nav-item {
      min-width: 180px;
    }

    .settings-grid,
    .setting-row {
      grid-template-columns: 1fr;
    }
  }
}
</style>
