import { DEFAULT_NATIVE_API_BASE } from './apiDefaults'

export const SETTINGS_STORAGE_KEY = 'fund-tracker-settings'

export type ColorModeSetting = 'red-up-green-down' | 'green-up-red-down'
export type DayCountModeSetting = 'trading' | 'calendar'

export interface AiProviderConfig {
  id: string
  name: string
  model: string
  baseUrl: string
  apiKey: string
  prompt: string
  updatedAt: number
}

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
  aiActiveConfigId: string
  aiConfigs: AiProviderConfig[]
}

export const DEFAULT_AI_MODEL = 'gpt-5.5'
export const DEFAULT_AI_CONFIG_ID = 'default'

const LEGACY_SIMPLE_PROMPT_MARKERS = [
  '请从这张持仓截图中提取基金持仓信息',
  '"holding_return": 收益数字',
  'market_value 是市值或持有金额'
]

export const DEFAULT_AI_PROMPT = `你是基金持仓截图识别器。请从图片中的“我的持有”基金列表提取所有基金持仓，返回严格 JSON，不要输出解释、Markdown 或代码块。

识别范围：
1. 只读取“我的持有”列表下的基金行，不要把顶部“总金额、昨日收益、持有收益、累计收益”当成基金。
2. 读取“全部(n)”中的 n 作为 expected_count；如果显示“全部(18)”，holdings 应尽量返回 18 条。
3. 每条基金按截图从上到下编号 row_index，从 1 开始；不要合并名称相似或重复出现的基金。

字段规则：
1. 左列是基金名称，名称可能分两行，必须合并；raw_fund_name 保留截图原始可见名称。
2. 中列第一行是当前金额 market_value，第二行是昨日收益 daily_return。
3. 右列第一行是持有收益 holding_return，第二行是持有收益率 holding_return_rate。
4. 红色加号是正数，绿色减号是负数，必须保留正负号；数字中的逗号去掉。
5. A类、C类、QDII、LOF、ETF、FOF、人民币等后缀会影响基金代码，能看到时必须保留。
6. 如果基金名称被省略号、括号或“...”截断，不要猜完整基金名或 A/C 类别，fund_name 和 raw_fund_name 都填写截图中可见文本。
7. 无法识别的金额填 0；无法识别的收益率填 null。

JSON 结构：
{
  "expected_count": 18,
  "holdings": [
    {
      "row_index": 1,
      "fund_name": "基金名称",
      "raw_fund_name": "截图原始可见基金名称",
      "market_value": 2100.95,
      "daily_return": 20.29,
      "holding_return": 76.46,
      "holding_return_rate": 3.97
    }
  ]
}`

export const DEFAULT_APP_SETTINGS: AppSettings = {
  language: 'zh-CN',
  apiUrl: DEFAULT_NATIVE_API_BASE,
  autoRefresh: false,
  refreshInterval: 60,
  colorMode: 'red-up-green-down',
  dayCountMode: 'trading',
  aiModel: DEFAULT_AI_MODEL,
  aiBaseUrl: '',
  aiApiKey: '',
  aiPrompt: DEFAULT_AI_PROMPT,
  aiActiveConfigId: DEFAULT_AI_CONFIG_ID,
  aiConfigs: [{
    id: DEFAULT_AI_CONFIG_ID,
    name: '默认配置',
    model: DEFAULT_AI_MODEL,
    baseUrl: '',
    apiKey: '',
    prompt: DEFAULT_AI_PROMPT,
    updatedAt: 0
  }]
}

function createDefaultAiConfig(): AiProviderConfig {
  return {
    ...DEFAULT_APP_SETTINGS.aiConfigs[0]!,
    updatedAt: Date.now()
  }
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

function createAiConfigId(): string {
  return `ai-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function normalizeAiPrompt(value: unknown): string {
  if (typeof value !== 'string' || !value.trim()) return DEFAULT_AI_PROMPT
  const prompt = value.trim()
  const isLegacySimplePrompt = LEGACY_SIMPLE_PROMPT_MARKERS.every(marker => prompt.includes(marker))
  return isLegacySimplePrompt ? DEFAULT_AI_PROMPT : prompt
}

function normalizeAiModel(value: unknown): string {
  if (typeof value !== 'string' || !value.trim()) return DEFAULT_AI_MODEL
  const model = value.trim()
  return /^gpt-/i.test(model) ? model.toLowerCase() : model
}

function normalizeAiConfig(value: Partial<AiProviderConfig> | undefined, fallbackName = '默认配置'): AiProviderConfig {
  return {
    id: typeof value?.id === 'string' && value.id.trim() ? value.id : createAiConfigId(),
    name: typeof value?.name === 'string' && value.name.trim() ? value.name.trim() : fallbackName,
    model: normalizeAiModel(value?.model),
    baseUrl: typeof value?.baseUrl === 'string' ? value.baseUrl.trim() : '',
    apiKey: typeof value?.apiKey === 'string' ? value.apiKey : '',
    prompt: normalizeAiPrompt(value?.prompt),
    updatedAt: typeof value?.updatedAt === 'number' ? value.updatedAt : Date.now()
  }
}

function buildAiConfigs(parsed: Partial<AppSettings>): { activeId: string; configs: AiProviderConfig[] } {
  const rawConfigs = Array.isArray(parsed.aiConfigs) ? parsed.aiConfigs as unknown[] : []
  const parsedConfigs = rawConfigs.length > 0
    ? rawConfigs
      .filter((item): item is Partial<AiProviderConfig> => item !== null && typeof item === 'object' && !Array.isArray(item))
      .map((item, index) => normalizeAiConfig(item, index === 0 ? '默认配置' : `配置 ${index + 1}`))
    : []

  const legacyModel = typeof parsed.aiModel === 'string' && parsed.aiModel.trim()
    ? normalizeAiModel(parsed.aiModel)
    : normalizeAiModel(readLocalStorage('ai_model'))
  const legacyBaseUrl = typeof parsed.aiBaseUrl === 'string'
    ? parsed.aiBaseUrl.trim()
    : readLocalStorage('ai_base_url').trim()
  const legacyApiKey = typeof parsed.aiApiKey === 'string'
    ? parsed.aiApiKey
    : readLocalStorage('ai_api_key')
  const legacyPrompt = typeof parsed.aiPrompt === 'string' && parsed.aiPrompt.trim()
    ? normalizeAiPrompt(parsed.aiPrompt)
    : normalizeAiPrompt(readLocalStorage('ai_prompt'))

  if (parsedConfigs.length === 0) {
    parsedConfigs.push(normalizeAiConfig({
      id: DEFAULT_AI_CONFIG_ID,
      name: '默认配置',
      model: legacyModel || DEFAULT_AI_MODEL,
      baseUrl: legacyBaseUrl,
      apiKey: legacyApiKey,
      prompt: legacyPrompt || DEFAULT_AI_PROMPT,
      updatedAt: Date.now()
    }))
  }

  const deduped: AiProviderConfig[] = []
  const seen = new Set<string>()
  for (const config of parsedConfigs) {
    let id = config.id
    if (seen.has(id)) {
      id = createAiConfigId()
    }
    seen.add(id)
    deduped.push({ ...config, id })
  }

  const requestedActiveId = typeof parsed.aiActiveConfigId === 'string' ? parsed.aiActiveConfigId : ''
  const active = deduped.find(config => config.id === requestedActiveId) ?? deduped[0]
  if (!active) {
    const fallback = createDefaultAiConfig()
    return {
      activeId: fallback.id,
      configs: [fallback]
    }
  }
  return {
    activeId: active.id,
    configs: deduped
  }
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

  const aiConfigState = buildAiConfigs(parsed)
  const activeAiConfig = aiConfigState.configs.find(config => config.id === aiConfigState.activeId) ?? aiConfigState.configs[0]
  if (!activeAiConfig) {
    throw new Error('AI配置初始化失败')
  }

  const merged = {
    ...DEFAULT_APP_SETTINGS,
    ...parsed,
    aiModel: activeAiConfig.model,
    aiBaseUrl: activeAiConfig.baseUrl,
    aiApiKey: activeAiConfig.apiKey,
    aiPrompt: activeAiConfig.prompt,
    aiActiveConfigId: activeAiConfig.id,
    aiConfigs: aiConfigState.configs
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
  const aiConfigs = settings.aiConfigs.length > 0 ? settings.aiConfigs : [createDefaultAiConfig()]
  const normalizedAiConfigs = aiConfigs.map(config => normalizeAiConfig(config))
  const activeConfig = normalizedAiConfigs.find(config => config.id === settings.aiActiveConfigId) ?? normalizedAiConfigs[0]
  if (!activeConfig) {
    throw new Error('AI配置保存失败')
  }
  const normalizedSettings: AppSettings = {
    ...settings,
    aiActiveConfigId: activeConfig.id,
    aiConfigs: normalizedAiConfigs,
    aiModel: activeConfig.model,
    aiBaseUrl: activeConfig.baseUrl,
    aiApiKey: activeConfig.apiKey,
    aiPrompt: activeConfig.prompt
  }

  writeLocalStorage(SETTINGS_STORAGE_KEY, JSON.stringify(normalizedSettings))
  writeLocalStorage('ai_model', activeConfig.model)
  writeLocalStorage('ai_base_url', activeConfig.baseUrl)
  writeLocalStorage('ai_api_key', activeConfig.apiKey)
  writeLocalStorage('ai_prompt', activeConfig.prompt)
}
