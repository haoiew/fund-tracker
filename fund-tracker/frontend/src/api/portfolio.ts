import { request } from './request'

// 类型定义
export interface PortfolioItem {
  id?: number
  fund_code: string
  fund_name?: string  // 可选，因为创建时可能不需要
  hold_shares: number  // 持有份额
  cost_amount: number  // 投入金额
  cost_nav?: number    // 成本净值
  buy_date?: string
  current_nav?: number // 当前净值
  current_change?: number | null
  current_value?: number // 当前市值
  profit_amount?: number // 持有收益
  profit_rate?: number   // 收益率
  daily_profit?: number  // 当日收益
  realtime_change_pct?: number | null
  realtime_change_amount?: number
  official_nav?: number | null
  official_change_pct?: number | null
  official_change_amount?: number
  official_value?: number | null
  official_update_time?: string | null
  data_kind?: string | null
  data_kind_label?: string | null
  is_realtime?: boolean
  transaction_count?: number
  remark?: string        // 备注
  created_at?: string
  updated_at?: string
}

export interface PortfolioStats {
  total_cost: number
  total_value: number
  total_profit_loss: number
  total_profit_loss_pct: number
  item_count: number
}

export interface PortfolioSummary {
  items: PortfolioItem[]
  stats: PortfolioStats
}

export type PortfolioImportMode = 'append' | 'overwrite' | 'rebalance'

export type PortfolioTransactionType = 'buy' | 'sell' | 'dividend' | 'snapshot'

export interface PortfolioRebalanceRecord {
  id: number
  fund_code: string
  fund_name: string
  action_type: 'new' | 'add' | 'increase' | 'decrease' | 'remove' | 'adjust' | string
  trade_date: string
  before_shares: number
  after_shares: number
  before_cost_amount: number
  after_cost_amount: number
  before_market_value: number
  after_market_value: number
  inferred_shares: number
  inferred_amount: number
  confidence: number
  source: string
  remark?: string | null
  created_at: string
}

// API 方法
export const portfolioApi = {
  // 获取所有持仓
  getAll(): Promise<PortfolioSummary> {
    return request.get('/portfolio/summary')
  },

  // 获取单个持仓
  getById(id: number): Promise<PortfolioItem> {
    return request.get(`/portfolio/${id}`)
  },

  // 添加持仓
  add(item: Omit<PortfolioItem, 'id' | 'created_at' | 'updated_at'>): Promise<PortfolioItem> {
    return request.post('/portfolio', item)
  },

  // 更新持仓
  update(id: number, item: Partial<PortfolioItem>): Promise<PortfolioItem> {
    return request.put(`/portfolio/${id}`, item)
  },

  // 删除持仓
  delete(id: number): Promise<void> {
    return request.delete(`/portfolio/${id}`)
  },

  // 刷新持仓数据
  refresh(): Promise<PortfolioSummary> {
    return request.post('/portfolio/refresh')
  },

  // 测试AI接口连通性和延迟
  testAiConnection(data: {
    model: string
    base_url: string
    api_key: string
    include_vision?: boolean
  }): Promise<{
    ok: boolean
    latency_ms?: number | null
    vision_latency_ms?: number | null
    status_code?: number | null
    model: string
    message: string
  }> {
    return request.post('/portfolio/ai-connection-test', data)
  },

  // AI识别持仓截图（后端一体化：AI识别+自动匹配基金代码）
  aiRecognize(data: {
    image_base64: string
    model: string
    base_url: string
    api_key: string
    prompt?: string
  }): Promise<{
    holdings: Array<{
      row_index?: number
      fund_code: string
      fund_name: string
      raw_fund_name: string
      market_value: number
      daily_return: number
      holding_return: number
      holding_return_rate: number | null
      match_status: string
      confidence: number
      match_reason: string
      warnings: string[]
      candidates: Array<{
        code: string
        name: string
        score: number
        reason: string
      }>
    }>
    total_value: number
    total_holding_return: number
    holdings_count: number
    expected_count?: number
    warnings: string[]
    ai_raw_content?: string
  }> {
    return request.post('/portfolio/ai-recognize', data, { timeout: 240000 })
  },

  aiRecognizeTransactions(data: {
    image_base64: string
    model: string
    base_url: string
    api_key: string
    prompt?: string
    default_year?: number
  }): Promise<{
    transactions: Array<{
      row_index?: number
      fund_code: string
      fund_name: string
      raw_fund_name: string
      transaction_type: PortfolioTransactionType
      trade_date: string
      trade_time?: string | null
      amount: number
      order_status: string
      match_status: string
      confidence: number
      match_reason: string
      warnings: string[]
      candidates: Array<{
        code: string
        name: string
        score: number
        reason: string
      }>
    }>
    expected_count?: number
    total_buy_amount: number
    total_sell_amount: number
    warnings: string[]
    ai_raw_content?: string
  }> {
    return request.post('/portfolio/ai-recognize-transactions', data, { timeout: 240000 })
  },

  previewImport(data: {
    holdings: Array<{
      row_index?: number
      fund_code?: string
      fund_name: string
      raw_fund_name?: string
      market_value: number
      daily_return?: number
      holding_return?: number
      holding_return_rate?: number | null
      match_status?: string
      confidence?: number
      match_reason?: string
    }>
    strict?: boolean
    mode?: PortfolioImportMode
  }): Promise<{
    items: Array<{
      row_index?: number
      fund_code: string
      fund_name: string
      raw_fund_name?: string
      market_value: number
      daily_return: number
      holding_return: number
      holding_return_rate?: number | null
      estimated_cost: number
      current_nav?: number | null
      current_change?: number | null
      estimated_shares?: number | null
      estimated_cost_nav?: number | null
      match_status?: string | null
      confidence?: number | null
      status: 'ready' | 'skipped' | 'invalid'
      reason: string
      warnings: string[]
      diff_type?: string | null
      existing_portfolio_id?: number | null
      existing_shares?: number | null
      existing_cost?: number | null
      inferred_amount?: number | null
      inferred_shares?: number | null
      confidence_score?: number | null
    }>
    ready_count: number
    skipped_count: number
    invalid_count: number
  }> {
    return request.post('/portfolio/import/preview', data)
  },

  confirmImport(data: {
    holdings: Array<{
      row_index?: number
      fund_code?: string
      fund_name: string
      raw_fund_name?: string
      market_value: number
      daily_return?: number
      holding_return?: number
      holding_return_rate?: number | null
      match_status?: string
      confidence?: number
      match_reason?: string
    }>
    strict?: boolean
    trade_date?: string
    mode?: PortfolioImportMode
  }): Promise<{
    items: Array<{
      row_index?: number
      fund_code: string
      fund_name: string
      status: 'success' | 'skipped' | 'failed'
      portfolio_id?: number | null
      error?: string | null
    }>
    success_count: number
    skipped_count: number
    failed_count: number
  }> {
    return request.post('/portfolio/import/confirm', data)
  },

  previewTransactionImport(data: {
    transactions: Array<{
      row_index?: number
      fund_code?: string
      fund_name: string
      raw_fund_name?: string
      transaction_type: PortfolioTransactionType
      trade_date: string
      trade_time?: string | null
      amount: number
      order_status?: string
      match_status?: string
      confidence?: number
      match_reason?: string
    }>
    strict?: boolean
  }): Promise<{
    items: Array<{
      row_index?: number
      fund_code?: string
      fund_name: string
      raw_fund_name?: string
      transaction_type: PortfolioTransactionType
      trade_date: string
      trade_time?: string | null
      amount: number
      order_status?: string | null
      current_nav?: number | null
      estimated_shares?: number | null
      status: 'ready' | 'skipped' | 'invalid'
      reason: string
      warnings: string[]
      existing_portfolio_id?: number | null
      match_status?: string | null
      confidence?: number | null
      match_reason?: string | null
    }>
    ready_count: number
    skipped_count: number
    invalid_count: number
  }> {
    return request.post('/portfolio/transactions/import/preview', data)
  },

  confirmTransactionImport(data: {
    transactions: Array<{
      row_index?: number
      fund_code?: string
      fund_name: string
      raw_fund_name?: string
      transaction_type: PortfolioTransactionType
      trade_date: string
      trade_time?: string | null
      amount: number
      order_status?: string
      match_status?: string
      confidence?: number
      match_reason?: string
    }>
    strict?: boolean
  }): Promise<{
    items: Array<{
      row_index?: number
      fund_code: string
      fund_name: string
      status: 'success' | 'skipped' | 'failed'
      transaction_id?: number | null
      portfolio_id?: number | null
      error?: string | null
    }>
    success_count: number
    skipped_count: number
    failed_count: number
  }> {
    return request.post('/portfolio/transactions/import/confirm', data)
  },

  getRebalanceRecords(limit = 200): Promise<PortfolioRebalanceRecord[]> {
    return request.get('/portfolio/rebalance-records', { params: { limit } })
  }
}

export default portfolioApi
