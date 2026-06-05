<template>
  <div class="settings-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">{{ $t('nav.settings') }}</span>
        </div>
      </template>

      <el-form label-width="150px">
        <!-- 外观设置 -->
        <div class="settings-section">
          <h3 class="section-title">{{ $t('settings.appearance') }}</h3>
          
          <el-form-item :label="$t('settings.language')">
            <el-radio-group v-model="settings.language" @change="changeLanguage">
              <el-radio-button value="zh-CN">中文</el-radio-button>
              <el-radio-button value="en-US">English</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item :label="$t('settings.theme')">
            <el-radio-group v-model="themeStore.theme" @change="handleThemeChange">
              <el-radio-button value="light">{{ $t('settings.light') }}</el-radio-button>
              <el-radio-button value="dark">{{ $t('settings.dark') }}</el-radio-button>
              <el-radio-button value="auto">{{ $t('settings.auto') }}</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="涨跌颜色">
            <el-radio-group v-model="settings.colorMode" @change="handleColorModeChange">
              <el-radio-button value="red-up-green-down">
                <span class="color-preview red-up">红涨绿跌</span>
              </el-radio-button>
              <el-radio-button value="green-up-red-down">
                <span class="color-preview green-up">绿涨红跌</span>
              </el-radio-button>
            </el-radio-group>
          </el-form-item>
        </div>

        <!-- 数据设置 -->
        <div class="settings-section">
          <h3 class="section-title">{{ $t('settings.data') }}</h3>

          <el-form-item :label="$t('settings.apiUrl')">
            <el-input v-model="settings.apiUrl" placeholder="http://localhost:8001/api/v1" />
          </el-form-item>

          <el-form-item :label="$t('settings.autoRefresh')">
            <el-switch v-model="settings.autoRefresh" class="auto-refresh-switch" />
          </el-form-item>

          <el-form-item :label="$t('settings.refreshInterval')" v-if="settings.autoRefresh">
            <el-slider v-model="settings.refreshInterval" :min="10" :max="300" :step="10" show-stops />
            <span class="slider-value">{{ settings.refreshInterval }}{{ $t('common.second') }}</span>
          </el-form-item>

          <el-form-item label="天数统计口径">
            <el-radio-group v-model="settings.dayCountMode">
              <el-radio value="trading">交易日</el-radio>
              <el-radio value="calendar">自然日</el-radio>
            </el-radio-group>
            <div class="form-tip">影响"N天内累计涨跌幅"筛选的天数计算方式</div>
          </el-form-item>
        </div>

        <!-- AI 模型设置 -->
        <div class="settings-section">
          <h3 class="section-title">AI 模型配置</h3>

          <el-form-item label="模型名称">
            <el-input v-model="settings.aiModel" placeholder="例如 gpt-4o、mimo-v2-pro" />
          </el-form-item>

          <el-form-item label="Base URL">
            <el-input v-model="settings.aiBaseUrl" placeholder="https://api.example.com/v1" />
          </el-form-item>

          <el-form-item label="API Key">
            <el-input v-model="settings.aiApiKey" type="password" show-password placeholder="sk-..." />
          </el-form-item>

          <el-form-item label="识别提示词">
            <el-input
              v-model="settings.aiPrompt"
              type="textarea"
              :rows="6"
              placeholder="用于识别持仓截图的提示词"
            />
          </el-form-item>
        </div>

        <!-- 关于 -->
        <div class="settings-section">
          <h3 class="section-title">{{ $t('settings.about') }}</h3>
          
          <el-form-item :label="$t('settings.version')">
            <span>v2.0.0</span>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="saveSettings">{{ $t('common.save') }}</el-button>
            <el-button @click="resetSettings">{{ $t('common.reset') }}</el-button>
          </el-form-item>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'SettingsView'
})

import { reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useThemeStore, type ThemeType } from '@/stores/themeStore'

const { locale, t } = useI18n()
const themeStore = useThemeStore()

const DEFAULT_AI_PROMPT = `请从这张持仓截图中提取基金持仓信息，返回严格的JSON格式，不要包含任何其他文字。
JSON结构要求：
{
  "holdings": [
    {"fund_name": "基金名称", "market_value": 市值数字, "holding_return": 收益数字}
  ]
}
如果某个字段无法识别，holding_return 设为 0。market_value 是市值或持有金额。`

const settings = reactive({
  language: 'zh-CN',
  apiUrl: 'http://localhost:8001/api/v1',
  autoRefresh: false,
  refreshInterval: 60,
  colorMode: 'red-up-green-down',
  dayCountMode: 'trading',
  aiModel: '',
  aiBaseUrl: '',
  aiApiKey: '',
  aiPrompt: DEFAULT_AI_PROMPT
})

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
  localStorage.setItem('fund-tracker-settings', JSON.stringify(settings))
  // 兼容旧的独立键
  localStorage.setItem('ai_model', settings.aiModel)
  localStorage.setItem('ai_base_url', settings.aiBaseUrl)
  localStorage.setItem('ai_api_key', settings.aiApiKey)
  localStorage.setItem('ai_prompt', settings.aiPrompt)
  ElMessage.success(t('settings.saved'))
}

const resetSettings = () => {
  settings.language = 'zh-CN'
  settings.apiUrl = 'http://localhost:8001/api/v1'
  settings.autoRefresh = false
  settings.refreshInterval = 60
  settings.colorMode = 'red-up-green-down'
  settings.dayCountMode = 'trading'
  settings.aiModel = ''
  settings.aiBaseUrl = ''
  settings.aiApiKey = ''
  settings.aiPrompt = DEFAULT_AI_PROMPT
  themeStore.setTheme('light')
  changeLanguage('zh-CN')
  localStorage.setItem('fund-tracker-color-mode', 'red-up-green-down')
  ElMessage.info(t('settings.reset'))
}

// 加载设置
onMounted(() => {
  const saved = localStorage.getItem('fund-tracker-settings')
  if (saved) {
    const parsed = JSON.parse(saved)
    settings.language = parsed.language ?? 'zh-CN'
    settings.apiUrl = parsed.apiUrl ?? 'http://localhost:8001/api/v1'
    settings.autoRefresh = parsed.autoRefresh ?? false
    settings.refreshInterval = parsed.refreshInterval ?? 60
    settings.colorMode = parsed.colorMode ?? 'red-up-green-down'
    settings.dayCountMode = parsed.dayCountMode ?? 'trading'
    settings.aiModel = parsed.aiModel ?? localStorage.getItem('ai_model') ?? ''
    settings.aiBaseUrl = parsed.aiBaseUrl ?? localStorage.getItem('ai_base_url') ?? ''
    settings.aiApiKey = parsed.aiApiKey ?? localStorage.getItem('ai_api_key') ?? ''
    settings.aiPrompt = parsed.aiPrompt ?? localStorage.getItem('ai_prompt') ?? DEFAULT_AI_PROMPT
  } else {
    // 兼容旧的独立键
    settings.aiModel = localStorage.getItem('ai_model') ?? ''
    settings.aiBaseUrl = localStorage.getItem('ai_base_url') ?? ''
    settings.aiApiKey = localStorage.getItem('ai_api_key') ?? ''
    settings.aiPrompt = localStorage.getItem('ai_prompt') ?? DEFAULT_AI_PROMPT
  }

  // 加载语言设置
  const savedLang = localStorage.getItem('fund-tracker-language')
  if (savedLang) {
    settings.language = savedLang
    locale.value = savedLang
  }

  // 加载颜色模式设置
  const savedColorMode = localStorage.getItem('fund-tracker-color-mode')
  if (savedColorMode) {
    settings.colorMode = savedColorMode
  }
})
</script>

<style scoped lang="scss">
.settings-view {
  .card-header {
    .title {
      font-size: var(--font-size-md);
      font-weight: 600;
    }
  }

  .settings-section {
    margin-bottom: 32px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .section-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0 0 20px 0;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-base);
    }
  }

  .slider-value {
    margin-left: 16px;
    color: var(--text-secondary);
  }

  .form-tip {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
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

  // 自动刷新开关样式
  .auto-refresh-switch {
    :deep(.el-switch__core) {
      background-color: var(--border-base);
      border-color: var(--border-base);
    }
    
    :deep(.el-switch__action) {
      background-color: var(--bg-card);
    }
    
    &.is-checked {
      :deep(.el-switch__core) {
        background-color: var(--primary-color);
        border-color: var(--primary-color);
      }
    }
  }
}
</style>
