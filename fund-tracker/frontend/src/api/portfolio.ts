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
  profit_amount?: number // 盈亏金额
  profit_rate?: number   // 收益率
  daily_profit?: number  // 当日收益
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
    return request.post('/portfolio/ai-recognize', data)
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
  }
}

export default portfolioApi
