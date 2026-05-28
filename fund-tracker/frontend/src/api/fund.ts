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
  data_timestamp?: string
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
    codes?: string[]
  ): Promise<{
    direction: string
    min_days: number
    min_pct: number
    count: number
    funds: FundTrendResult[]
  }> {
    const params: Record<string, any> = {
      min_days: minDays,
      min_pct: minPct
    }
    if (codes && codes.length > 0) {
      params.codes = codes.join(',')
    }
    return request.get(`/funds/screen/${direction}`, { params })
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
      priority: number
      estimate_nav: number | null
      estimate_change_pct: number | null
      last_nav: number | null
      last_change_pct: number | null
      update_time: string
      is_fresh: boolean
    }>
    best_source: string | null
    total_sources: number
  }> {
    const params: Record<string, any> = {}
    if (name) {
      params.name = name
    }
    return request.get(`/funds/${code}/data-sources`, { params })
  }
}

export default fundApi
