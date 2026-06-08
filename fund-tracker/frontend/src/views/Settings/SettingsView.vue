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
                <span>配置档案</span>
                <small>保存多套 OpenAI 兼容接口配置，按使用场景快速切换</small>
              </div>
              <div class="ai-profile-control">
                <el-select
                  v-model="settings.aiActiveConfigId"
                  class="ai-profile-select"
                  placeholder="选择配置"
                  @change="switchAiConfig"
                >
                  <el-option
                    v-for="config in settings.aiConfigs"
                    :key="config.id"
                    :label="`${config.name} · ${config.model || '未设置模型'}`"
                    :value="config.id"
                  />
                </el-select>
                <div class="ai-profile-actions">
                  <el-button :icon="Check" @click="saveCurrentAiConfig">保存当前</el-button>
                  <el-button :icon="CopyDocument" @click="saveAsNewAiConfig">另存为</el-button>
                  <el-button :icon="Delete" :disabled="settings.aiConfigs.length <= 1" @click="deleteCurrentAiConfig">删除</el-button>
                </div>
              </div>
            </div>

            <div class="setting-row">
              <div>
                <span>配置名称</span>
                <small>用于区分不同服务商、账号或模型组合</small>
              </div>
              <el-input v-model="activeAiConfigName" placeholder="例如 OpenAI 主账号、备用中转、硅基流动" />
            </div>

            <div class="setting-row">
              <div>
                <span>模型名称</span>
                <small>用于持仓截图识别的模型标识</small>
              </div>
              <div class="inline-control">
                <el-input v-model="settings.aiModel" placeholder="例如 gpt-5.5" />
                <el-button @click="useRecommendedAiModel">使用推荐</el-button>
              </div>
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

            <div class="setting-row">
              <div>
                <span>连通性检测</span>
                <small>由后端实际请求模型服务，返回接口可用性和延迟</small>
              </div>
              <div class="ai-test-control">
                <el-checkbox v-model="aiVisionTestEnabled">
                  同时测试图片输入能力
                </el-checkbox>
                <el-button type="primary" :icon="Timer" :loading="aiTestLoading" @click="testAiConnection">测试连接</el-button>
                <el-alert
                  v-if="aiTestResult"
                  class="ai-test-result"
                  :type="aiTestResult.ok ? 'success' : 'error'"
                  :closable="false"
                  show-icon
                >
                  <template #title>
                    {{ aiTestResult.message }}
                    <span v-if="aiTestResult.latencyMs !== null"> · 文本 {{ aiTestResult.latencyMs }}ms</span>
                    <span v-if="aiTestResult.visionLatencyMs !== null"> · 图片 {{ aiTestResult.visionLatencyMs }}ms</span>
                  </template>
                </el-alert>
              </div>
            </div>

            <div class="setting-row is-vertical">
              <div>
                <span>识别提示词</span>
                <small>约束截图识别输出 JSON 结构</small>
              </div>
              <div class="prompt-actions">
                <el-button size="small" @click="restoreRecommendedPrompt">恢复推荐提示词</el-button>
              </div>
              <el-input
                v-model="settings.aiPrompt"
                type="textarea"
                :rows="16"
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { useThemeStore, type ThemeType } from '@/stores/themeStore'
import { Brush, Check, Coin, CopyDocument, Delete, InfoFilled, MagicStick, Setting, Timer } from '@element-plus/icons-vue'
import {
  DEFAULT_APP_SETTINGS,
  DEFAULT_AI_MODEL,
  DEFAULT_AI_PROMPT,
  loadAppSettings,
  saveAppSettings,
  type AiProviderConfig,
  type AppSettings
} from '@/platform/appSettings'
import portfolioApi from '@/api/portfolio'

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

const cloneDefaultSettings = (): AppSettings => JSON.parse(JSON.stringify(DEFAULT_APP_SETTINGS)) as AppSettings

const settings = reactive<AppSettings>(cloneDefaultSettings())
const lastActiveAiConfigId = ref(settings.aiActiveConfigId)
const aiDraftName = ref('')
const aiTestLoading = ref(false)
const aiVisionTestEnabled = ref(true)
const aiTestResult = ref<{ ok: boolean; message: string; latencyMs: number | null; visionLatencyMs: number | null } | null>(null)

const activeAiConfig = computed(() => {
  return settings.aiConfigs.find(config => config.id === settings.aiActiveConfigId) ?? settings.aiConfigs[0]
})

const activeAiConfigName = computed({
  get: () => aiDraftName.value,
  set: (value: string) => {
    aiDraftName.value = value
  }
})

const createAiConfigId = () => `ai-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const applyAiConfigToFields = (config: AiProviderConfig) => {
  aiDraftName.value = config.name
  settings.aiModel = config.model
  settings.aiBaseUrl = config.baseUrl
  settings.aiApiKey = config.apiKey
  settings.aiPrompt = config.prompt?.trim() || DEFAULT_AI_PROMPT
  aiTestResult.value = null
}

const syncCurrentAiConfig = (configId = settings.aiActiveConfigId) => {
  const target = settings.aiConfigs.find(config => config.id === configId)
  if (!target) return
  target.name = aiDraftName.value.trim() || '未命名配置'
  target.model = settings.aiModel.trim()
  target.baseUrl = settings.aiBaseUrl.trim()
  target.apiKey = settings.aiApiKey
  target.prompt = settings.aiPrompt?.trim() || DEFAULT_AI_PROMPT
  target.updatedAt = Date.now()
}

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

const useRecommendedAiModel = () => {
  settings.aiModel = DEFAULT_AI_MODEL
  aiTestResult.value = null
  ElMessage.success('已填入推荐模型')
}

const restoreRecommendedPrompt = () => {
  settings.aiPrompt = DEFAULT_AI_PROMPT
  ElMessage.success('已恢复推荐提示词')
}

const switchAiConfig = (configId: string) => {
  const next = settings.aiConfigs.find(config => config.id === configId)
  if (!next) return
  applyAiConfigToFields(next)
  lastActiveAiConfigId.value = next.id
}

const saveCurrentAiConfig = () => {
  syncCurrentAiConfig()
  saveAppSettings({ ...settings, aiConfigs: [...settings.aiConfigs] })
  ElMessage.success('当前 AI 配置已保存')
}

const saveAsNewAiConfig = () => {
  const nextIndex = settings.aiConfigs.length + 1
  const newConfig: AiProviderConfig = {
    id: createAiConfigId(),
    name: aiDraftName.value.trim() || `配置 ${nextIndex}`,
    model: settings.aiModel.trim() || DEFAULT_AI_MODEL,
    baseUrl: settings.aiBaseUrl.trim(),
    apiKey: settings.aiApiKey,
    prompt: settings.aiPrompt?.trim() || DEFAULT_AI_PROMPT,
    updatedAt: Date.now()
  }

  settings.aiConfigs.push(newConfig)
  settings.aiActiveConfigId = newConfig.id
  lastActiveAiConfigId.value = newConfig.id
  saveAppSettings({ ...settings, aiConfigs: [...settings.aiConfigs] })
  ElMessage.success(`已另存为 ${newConfig.name}`)
}

const deleteCurrentAiConfig = async () => {
  if (settings.aiConfigs.length <= 1 || !activeAiConfig.value) {
    ElMessage.warning('至少保留一套 AI 配置')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定删除“${activeAiConfig.value.name}”吗？`,
      '删除 AI 配置',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }

  const deletedId = activeAiConfig.value.id
  const index = settings.aiConfigs.findIndex(config => config.id === deletedId)
  settings.aiConfigs.splice(index, 1)
  const next = settings.aiConfigs[Math.max(0, index - 1)] ?? settings.aiConfigs[0]
  if (!next) return
  settings.aiActiveConfigId = next.id
  lastActiveAiConfigId.value = next.id
  applyAiConfigToFields(next)
  saveAppSettings({ ...settings, aiConfigs: [...settings.aiConfigs] })
  ElMessage.success('AI 配置已删除')
}

const testAiConnection = async () => {
  if (!settings.aiModel.trim() || !settings.aiBaseUrl.trim() || !settings.aiApiKey.trim()) {
    aiTestResult.value = {
      ok: false,
      message: '请先填写模型名称、Base URL 和 API Key',
      latencyMs: null,
      visionLatencyMs: null
    }
    ElMessage.warning(aiTestResult.value.message)
    return
  }

  aiTestLoading.value = true
  aiTestResult.value = null
  try {
    const result = await portfolioApi.testAiConnection({
      model: settings.aiModel.trim(),
      base_url: settings.aiBaseUrl.trim(),
      api_key: settings.aiApiKey,
      include_vision: aiVisionTestEnabled.value
    })

    aiTestResult.value = {
      ok: result.ok,
      message: result.message || '连接成功',
      latencyMs: result.latency_ms ?? null,
      visionLatencyMs: result.vision_latency_ms ?? null
    }
    ElMessage.success(`AI 接口连接成功${result.latency_ms ? `，延迟 ${result.latency_ms}ms` : ''}`)
  } catch (error) {
    const message = error instanceof Error ? error.message : '连接失败，请检查配置'
    aiTestResult.value = {
      ok: false,
      message,
      latencyMs: null,
      visionLatencyMs: null
    }
    ElMessage.error(`AI 接口连接失败：${message}`)
  } finally {
    aiTestLoading.value = false
  }
}

const saveSettings = () => {
  syncCurrentAiConfig()
  saveAppSettings({ ...settings })
  localStorage.setItem('fund-tracker-language', settings.language)
  localStorage.setItem('fund-tracker-color-mode', settings.colorMode)
  ElMessage.success(t('settings.saved'))
}

const resetSettings = () => {
  Object.assign(settings, cloneDefaultSettings())
  lastActiveAiConfigId.value = settings.aiActiveConfigId
  if (activeAiConfig.value) {
    applyAiConfigToFields(activeAiConfig.value)
  }
  themeStore.setTheme('light')
  changeLanguage('zh-CN')
  localStorage.setItem('fund-tracker-color-mode', 'red-up-green-down')
  ElMessage.info(t('settings.reset'))
}

// 加载设置
onMounted(() => {
  Object.assign(settings, loadAppSettings())
  lastActiveAiConfigId.value = settings.aiActiveConfigId
  if (activeAiConfig.value) {
    applyAiConfigToFields(activeAiConfig.value)
  }

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

  .inline-control {
    display: flex;
    align-items: center;
    gap: 10px;

    .el-input {
      flex: 1;
    }
  }

  .ai-profile-control {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .ai-profile-select {
    flex: 1;
    min-width: 220px;
  }

  .ai-profile-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .ai-test-control {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    min-width: 0;
  }

  .ai-test-result {
    width: 100%;
  }

  .prompt-actions {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 8px;
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

    .ai-profile-control,
    .inline-control {
      align-items: stretch;
      flex-direction: column;
    }

    .ai-profile-select {
      width: 100%;
      min-width: 0;
    }

    .ai-profile-actions {
      width: 100%;

      .el-button {
        flex: 1;
      }
    }
  }
}
</style>
