import { request } from './request'

// 类型定义
export interface FundRealtimeData {
  code: string
  name: string
  estimate_nav: number | null
  estimate_change: number | null
  update_time: string
  status: string
  data_source?: string
  data_source_display_name?: string
  data_source_short_name?: string
  data_source_description?: string
  data_kind?: 'realtime_estimate' | 'latest_nav' | 'holdings_estimate' | 'reference_symbol_estimate' | 'fallback_estimate' | 'similar_realtime_reference'
  data_kind_label?: string
  is_realtime?: boolean
  data_timestamp?: string
  official_nav?: number | null
  official_change?: number | null
  official_update_time?: string | null
  official_data_kind_label?: string | null
  // 新增字段
  previous_nav?: number | null
  accumulated_nav?: number | null
  daily_growth?: number | null
}

export interface FundChartData {
  dates: string[]
  values: number[]
  changes: number[]
}

export interface FundTrendResult {
  code: string
  name: string
  days: number
  pct: number
}

export type ScreenType = 'consecutive' | 'period'
export type ScreenUniverse = 'local' | 'market'

export interface ScreenCondition {
  id: string
  type: ScreenType
  direction: 'up' | 'down'
  minDays?: number
  minPct: number
  periodDays?: number
}

export interface ScreenResult {
  conditionId: string
  direction: string
  count: number
  funds: FundTrendResult[]
}

export interface FundSearchItem {
  code: string
  name: string
}

export interface FundCompareResult {
  code: string
  name: string
  chart_data: FundChartData
  current_change: number | null
}

export interface RealtimeAlternativeResult {
  code: string
  name: string
  direct: {
    change_pct: number | null
    update_time: string
    source: string
    data_kind: string
    is_realtime: boolean
  }
  skipped: boolean
  reason: string
  same_name_realtime_candidates: Array<{
    code: string
    name: string
    change_pct: number | null
    update_time: string
    source: string
    is_realtime: boolean
  }>
  exchange_or_quote_sources: Array<{
    source: string
    display_name?: string
    change_pct: number | null
    update_time: string
    is_realtime: boolean
  }>
  holdings_based_estimate: {
    feasible: boolean
    reason: string
    holding_count?: number
    position_date?: string
    quoted_count?: number
    quoted_weight_coverage?: number
    weighted_stock_change_pct?: number | null
    top_holdings?: Array<{
      code: string
      name: string
      weight: number
      holding_type?: string | null
      quote_change_pct: number | null
    }>
  } | null
  reference_symbol_estimate?: {
    feasible: boolean
    reason: string
    reference_count?: number
    weighted_stock_change_pct?: number | null
    references?: Array<{
      symbol: string
      name: string
      kind: string
      quote_change_pct?: number | null
    }>
  } | null
  fallback_estimate?: {
    feasible: boolean
    reason: string
    source?: string | null
    change_pct?: number | null
    update_time?: string | null
    data_kind?: string
    is_realtime?: boolean
  } | null
}

// API 方法
export const fundApi = {
  // 获取基金列表
  getFundList(): Promise<string[]> {
    return request.get('/funds/list')
  },

  // 添加基金
  addFund(code: string): Promise<{ code: string; success: boolean }> {
    return request.post('/funds/list/add', null, { params: { code } })
  },

  // 移除基金
  removeFund(code: string): Promise<{ code: string; success: boolean }> {
    return request.post('/funds/list/remove', null, { params: { code } })
  },

  // 获取基金实时估值
  getRealtime(code: string): Promise<FundRealtimeData> {
    return request.get(`/funds/realtime/${code}`)
  },

  // 批量获取实时估值
  getRealtimeBatch(codes: string[]): Promise<FundRealtimeData[]> {
    return request.post('/funds/realtime/batch', codes)
  },

  // 获取基金历史数据
  getHistory(code: string, range: string = '3M'): Promise<{
    data: FundChartData
    source: string
    updating: boolean
  }> {
    return request.get(`/funds/${code}/history?range=${range}`)
  },

  // 搜索基金
  search(keyword: string, limit: number = 10): Promise<FundSearchItem[]> {
    return request.post('/funds/search', { keyword, limit })
  },

  // 筛选基金（简化接口）
  screen(
    direction: 'up' | 'down',
    minDays: number = 2,
    minPct: number = 0.03,
    codes?: string[],
    includeRealtime: boolean = false,
    universe: ScreenUniverse = 'local',
    limit?: number
  ): Promise<{
    direction: string
    min_days: number
    min_pct: number
    count: number
    funds: FundTrendResult[]
  }> {
    const params: Record<string, string | number | boolean> = {
      min_days: minDays,
      min_pct: minPct,
      include_realtime: includeRealtime,
      universe
    }
    if (limit !== undefined) {
      params.limit = limit
    }
    if (codes && codes.length > 0) {
      params.codes = codes.join(',')
    }
    return request.get(`/funds/screen/${direction}`, { params })
  },

  // 筛选基金（N天内累计涨跌幅）
  screenPeriod(
    direction: 'up' | 'down',
    periodDays: number = 7,
    minPct: number = 0.03,
    codes?: string[],
    includeRealtime: boolean = false,
    calendarDays: boolean = false,
    universe: ScreenUniverse = 'local',
    limit?: number
  ): Promise<{
    direction: string
    period_days: number
    min_pct: number
    count: number
    funds: FundTrendResult[]
  }> {
    return request.post('/funds/screen/period', {
      direction,
      period_days: periodDays,
      min_pct: minPct,
      codes: codes && codes.length > 0 ? codes : undefined,
      include_realtime: includeRealtime,
      calendar_days: calendarDays,
      universe,
      limit
    })
  },

  // 对比基金
  compare(
    codes: string[],
    range: string = '3M',
    includeBenchmark = true
  ): Promise<{
    funds: Array<{
      code: string
      name: string
      dates: string[]
      changes: number[]
    }>
    benchmarks: Array<{
      name: string
      symbol: string
      dates: string[]
      changes: number[]
    }>
    range: string
  }> {
    return request.post('/funds/compare', { codes, range, include_benchmark: includeBenchmark })
  },

  // 获取默认基金列表
  getDefaultList(): Promise<string[]> {
    return request.get('/funds/default-list')
  },

  // 获取基金所有数据源对比
  getDataSources(code: string, name?: string): Promise<{
    code: string
    name: string
    sources: Array<{
      source: string
      display_name?: string
      short_name?: string
      description?: string
      priority: number
      name?: string | null
      estimate_nav: number | null
      estimate_change_pct: number | null
      last_nav: number | null
      last_change_pct: number | null
      update_time: string
      data_kind?: FundRealtimeData['data_kind']
      data_kind_label?: string
      is_realtime?: boolean
      is_fresh: boolean
      error?: string | null
    }>
    best_source: string | null
    best_source_display_name?: string | null
    total_sources: number
  }> {
    const params: Record<string, string> = {}
    if (name) {
      params.name = name
    }
    return request.get(`/funds/${code}/data-sources`, { params })
  },

  // 获取无真实实时估值时的替代方案
  getRealtimeAlternatives(code: string, name?: string): Promise<RealtimeAlternativeResult> {
    const params: Record<string, string> = {}
    if (name) {
      params.name = name
    }
    return request.get(`/funds/${code}/realtime-alternatives`, { params })
  }
}

export default fundApi
