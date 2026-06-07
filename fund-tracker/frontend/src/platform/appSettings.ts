import { DEFAULT_NATIVE_API_BASE } from './apiDefaults'

export const SETTINGS_STORAGE_KEY = 'fund-tracker-settings'

export type ColorModeSetting = 'red-up-green-down' | 'green-up-red-down'
export type DayCountModeSetting = 'trading' | 'calendar'

export interface AppSettings {
  language: string
  apiUrl: string
  autoRefresh: boolean
  refreshInterval: number
  colorMode: ColorModeSetting
  dayCountMode: DayCountModeSetting
  aiModel: string
  aiBaseUrl: string
  aiApiKey: string
  aiPrompt: string
}

export const DEFAULT_AI_PROMPT = `请从这张持仓截图中提取基金持仓信息，返回严格的JSON格式，不要包含任何其他文字。
JSON结构要求：
{
  "holdings": [
    {"fund_name": "基金名称", "market_value": 市值数字, "holding_return": 收益数字}
  ]
}
要求：
1. 只需要识别基金名称，不需要基金代码（系统会自动匹配）
2. market_value 是当前市值或持有金额
3. holding_return 是持有收益，如果无法识别则设为 0`

export const DEFAULT_APP_SETTINGS: AppSettings = {
  language: 'zh-CN',
  apiUrl: DEFAULT_NATIVE_API_BASE,
  autoRefresh: false,
  refreshInterval: 60,
  colorMode: 'red-up-green-down',
  dayCountMode: 'trading',
  aiModel: '',
  aiBaseUrl: '',
  aiApiKey: '',
  aiPrompt: DEFAULT_AI_PROMPT
}

function readLocalStorage(key: string): string {
  try {
    return window.localStorage.getItem(key) ?? ''
  } catch {
    return ''
  }
}

function writeLocalStorage(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // Storage can be unavailable in hardened WebViews. Keep runtime alive.
  }
}

function normalizeColorMode(value: unknown): ColorModeSetting {
  return value === 'green-up-red-down' ? 'green-up-red-down' : 'red-up-green-down'
}

function normalizeDayCountMode(value: unknown): DayCountModeSetting {
  return value === 'calendar' ? 'calendar' : 'trading'
}

export function loadAppSettings(): AppSettings {
  const saved = readLocalStorage(SETTINGS_STORAGE_KEY)
  let parsed: Partial<AppSettings> = {}

  if (saved) {
    try {
      parsed = JSON.parse(saved) as Partial<AppSettings>
    } catch {
      parsed = {}
    }
  }

  const merged = {
    ...DEFAULT_APP_SETTINGS,
    ...parsed,
    aiModel: parsed.aiModel ?? readLocalStorage('ai_model') ?? DEFAULT_APP_SETTINGS.aiModel,
    aiBaseUrl: parsed.aiBaseUrl ?? readLocalStorage('ai_base_url') ?? DEFAULT_APP_SETTINGS.aiBaseUrl,
    aiApiKey: parsed.aiApiKey ?? readLocalStorage('ai_api_key') ?? DEFAULT_APP_SETTINGS.aiApiKey,
    aiPrompt: parsed.aiPrompt ?? readLocalStorage('ai_prompt') ?? DEFAULT_APP_SETTINGS.aiPrompt
  }

  return {
    ...merged,
    colorMode: normalizeColorMode(merged.colorMode),
    dayCountMode: normalizeDayCountMode(merged.dayCountMode)
  }
}

export function loadConfiguredApiUrl(): string {
  const saved = readLocalStorage(SETTINGS_STORAGE_KEY)
  if (!saved) return ''

  try {
    const parsed = JSON.parse(saved) as Partial<AppSettings>
    return parsed.apiUrl?.trim() ?? ''
  } catch {
    return ''
  }
}

export function saveAppSettings(settings: AppSettings): void {
  writeLocalStorage(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
  writeLocalStorage('ai_model', settings.aiModel)
  writeLocalStorage('ai_base_url', settings.aiBaseUrl)
  writeLocalStorage('ai_api_key', settings.aiApiKey)
  writeLocalStorage('ai_prompt', settings.aiPrompt)
}
