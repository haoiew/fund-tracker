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
  }
}

export default portfolioApi
