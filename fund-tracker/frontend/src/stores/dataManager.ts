/**
 * 统一数据管理器
 * 管理所有基金相关数据，实现数据互通和共享
 * 支持页面刷新后数据不丢失（localStorage 持久化）
 */

import { reactive, computed } from 'vue'
import fundApi, { type FundRealtimeData, type RealtimeAlternativeResult } from '@/api/fund'
import portfolioApi, { type PortfolioItem, type PortfolioStats } from '@/api/portfolio'

// 数据管理器状态
interface DataManagerState {
  fundList: string[]
  fundListLoaded: boolean
  fundListLoading: boolean
  fundListError: string | null

  realtimeData: Map<string, FundRealtimeData>
  realtimeLoading: boolean
  realtimeLastFetch: number
  realtimeError: string | null

  portfolioItems: PortfolioItem[]
  portfolioStats: PortfolioStats | null
  portfolioLoaded: boolean
  portfolioLoading: boolean
  portfolioLastFetch: number
  portfolioError: string | null
}

// localStorage Key 常量
const STORAGE_KEYS = {
  FUND_LIST: 'fund_tracker_fund_list',
  FUND_LIST_DIRTY: 'fund_tracker_fund_list_dirty',  // 标记用户是否手动修改过列表
  REALTIME_DATA: 'fund_tracker_realtime_data',
  REALTIME_FETCH_TIME: 'fund_tracker_realtime_fetch_time',
  PORTFOLIO_ITEMS: 'fund_tracker_portfolio_items',
  PORTFOLIO_STATS: 'fund_tracker_portfolio_stats',
  PORTFOLIO_FETCH_TIME: 'fund_tracker_portfolio_fetch_time'
}

// 缓存配置（持久化时间）
const CACHE_TTL = {
  FUND_LIST: 5 * 60 * 1000,      // 基金列表缓存5分钟
  REALTIME: 5 * 60 * 1000,       // 实时数据缓存5分钟（用于刷新后快速显示）
  PORTFOLIO: 10 * 60 * 1000      // 持仓数据缓存10分钟
}

// 创建响应式状态
const state = reactive<DataManagerState>({
  fundList: [],
  fundListLoaded: false,
  fundListLoading: false,
  fundListError: null,

  realtimeData: new Map(),
  realtimeLoading: false,
  realtimeLastFetch: 0,
  realtimeError: null,

  portfolioItems: [],
  portfolioStats: null,
  portfolioLoaded: false,
  portfolioLoading: false,
  portfolioLastFetch: 0,
  portfolioError: null
})

type PortfolioLoadResult = { items: PortfolioItem[], stats: PortfolioStats }

// 正在进行的请求跟踪
const pendingRequests = new Map<string, Promise<unknown>>()

function getPendingRequest<T>(key: string): Promise<T> | undefined {
  return pendingRequests.get(key) as Promise<T> | undefined
}

function setPendingRequest<T>(key: string, request: Promise<T>): void {
  pendingRequests.set(key, request)
}

// 缓存统计
const cacheStats = {
  hits: 0,
  misses: 0,
  total: 0
}

class DataManager {
  // ============ 计算属性 ============

  getFundList = computed(() => state.fundList)
  isFundListLoaded = computed(() => state.fundListLoaded)
  getAllRealtimeData = computed(() => Array.from(state.realtimeData.values()))
  getPortfolioItems = computed(() => state.portfolioItems)
  getPortfolioStats = computed(() => state.portfolioStats)
  isPortfolioLoaded = computed(() => state.portfolioLoaded)

  getPortfolioWithRealtime = computed(() => {
    return state.portfolioItems.map(item => {
      const realtime = state.realtimeData.get(item.fund_code)

      // 获取基础数据
      const holdShares = Number(item.hold_shares) || 0
      const costAmount = Number(item.cost_amount) || 0
      const costNav = Number(item.cost_nav) || 0

      // 如果有实时数据，使用实时数据计算
      if (realtime?.estimate_nav && realtime.estimate_nav > 0) {
        const estimateNav = Number(realtime.estimate_nav)
        const currentValue = estimateNav * holdShares
        const profitAmount = currentValue - costAmount
        const profitRate = costNav > 0 ? ((estimateNav - costNav) / costNav * 100) : 0

        return {
          ...item,
          current_nav: estimateNav,
          current_change: realtime.estimate_change !== null ? Number(realtime.estimate_change) : null,
          current_value: currentValue,
          profit_amount: profitAmount,
          profit_rate: profitRate
        }
      }

      // 没有实时数据，使用后端返回的数据或计算默认值
      const currentNav = item.current_nav || costNav
      const currentValue = item.current_value || (currentNav * holdShares) || costAmount
      const profitAmount = (item.profit_amount !== undefined) ? item.profit_amount : (currentValue - costAmount)
      const profitRate = (item.profit_rate !== undefined) ? item.profit_rate :
                        (costNav > 0 && currentNav > 0 ? ((currentNav - costNav) / costNav * 100) : 0)

      return {
        ...item,
        current_nav: currentNav || null,
        current_value: currentValue || null,
        profit_amount: profitAmount,
        profit_rate: profitRate
      }
    })
  })

  // ============ 初始化方法 ============

  /**
   * 初始化所有数据
   * 策略：先从 localStorage 恢复，后台异步刷新最新数据
   */
  async initialize(): Promise<void> {
    console.log('[DataManager] 初始化数据...')

    try {
      // 1. 立即从本地存储恢复数据（无网络请求，瞬间完成）
      this.restoreFromStorage()

      // 2. 后台异步刷新最新数据
      this.refreshFromAPI()

      console.log('[DataManager] 数据初始化完成')
    } catch (e) {
      console.error('[DataManager] 数据初始化失败:', e)
    }
  }

  /**
   * 从本地存储恢复数据（并行执行）
   */
  private restoreFromStorage(): void {
    // 并行恢复所有数据（localStorage读取是同步的，但逻辑上并行）
    const results = [
      this.loadFundListFromStorage(),
      this.loadRealtimeDataFromStorage(),
      this.loadPortfolioFromStorage()
    ]

    const restored = results.filter(Boolean).length
    if (restored > 0) {
      console.log(`[DataManager] ✅ 从本地存储恢复数据: ${restored} 项`)
    }
  }

  /**
   * 后台异步刷新数据
   */
  private async refreshFromAPI(): Promise<void> {
    console.log('[DataManager] 🚀 并行刷新API数据...')
    const startTime = Date.now()

    // 并行刷新所有数据
    const promises: Promise<unknown>[] = [
      this.loadFundList().catch(e => {
        console.warn('[DataManager] 刷新基金列表失败:', e)
      }),
      this.loadPortfolio().catch(e => {
        console.warn('[DataManager] 刷新持仓数据失败:', e)
      })
    ]

    // 如果有基金列表，也刷新实时数据
    if (state.fundList.length > 0) {
      promises.push(
        this.loadRealtimeData().catch(e => {
          console.warn('[DataManager] 刷新实时数据失败:', e)
        })
      )
    }

    // 等待所有请求完成
    await Promise.all(promises)

    const elapsed = Date.now() - startTime
    console.log(`[DataManager] ✅ 并行刷新完成，耗时: ${elapsed}ms`)
  }

  // ============ 基金列表操作 ============

  /**
   * 加载基金列表
   */
  async loadFundList(forceRefresh = false): Promise<string[]> {
    // 用户手动修改过列表（包括清空），信任本地数据，不从API覆盖
    const isDirty = localStorage.getItem(STORAGE_KEYS.FUND_LIST_DIRTY) === 'true'

    if (state.fundListLoaded && !forceRefresh && (state.fundList.length > 0 || isDirty)) {
      console.log('[DataManager] 使用已加载的基金列表:', state.fundList.length)
      return state.fundList
    }

    const requestKey = 'fundList'
    const pendingRequest = getPendingRequest<string[]>(requestKey)
    if (pendingRequest) {
      return pendingRequest
    }

    state.fundListLoading = true
    const request = this.fetchFundListFromAPI()
    setPendingRequest(requestKey, request)

    try {
      const result = await request
      return result
    } finally {
      pendingRequests.delete(requestKey)
      state.fundListLoading = false
    }
  }

  /**
   * 从本地存储恢复基金列表
   */
  private loadFundListFromStorage(): boolean {
    // 如果用户手动修改过列表（添加/删除），则信任本地数据（包括空数组）
    const isDirty = localStorage.getItem(STORAGE_KEYS.FUND_LIST_DIRTY) === 'true'
    const stored = localStorage.getItem(STORAGE_KEYS.FUND_LIST)

    if (stored !== null) {
      try {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && (parsed.length > 0 || isDirty)) {
          state.fundList = parsed
          state.fundListLoaded = true
          console.log('[DataManager] 从本地存储恢复基金列表:', parsed.length)
          return true
        }
      } catch (e) {
        console.warn('[DataManager] 恢复基金列表失败:', e)
      }
    }
    return false
  }

  private async fetchFundListFromAPI(): Promise<string[]> {
    try {
      console.log('[DataManager] 从API获取基金列表...')
      const data = await fundApi.getDefaultList()
      state.fundList = data
      state.fundListLoaded = true
      state.fundListError = null

      // 保存到本地存储
      localStorage.setItem(STORAGE_KEYS.FUND_LIST, JSON.stringify(data))
      console.log('[DataManager] 基金列表加载完成:', data.length)

      return data
    } catch (e) {
      console.error('[DataManager] 获取基金列表失败:', e)
      // 只有在没有本地缓存时才设置错误
      if (state.fundList.length === 0) {
        state.fundListError = '获取基金列表失败'
      }
      throw e
    }
  }

  addFund(code: string) {
    if (!state.fundList.includes(code)) {
      state.fundList.push(code)
      localStorage.setItem(STORAGE_KEYS.FUND_LIST, JSON.stringify(state.fundList))
      localStorage.setItem(STORAGE_KEYS.FUND_LIST_DIRTY, 'true')
      console.log('[DataManager] 添加基金:', code)
    }
  }

  removeFund(code: string) {
    const index = state.fundList.indexOf(code)
    if (index > -1) {
      state.fundList.splice(index, 1)
      localStorage.setItem(STORAGE_KEYS.FUND_LIST, JSON.stringify(state.fundList))
      localStorage.setItem(STORAGE_KEYS.FUND_LIST_DIRTY, 'true')

      state.realtimeData.delete(code)
      const realtimeArray = Array.from(state.realtimeData.values())
      localStorage.setItem(STORAGE_KEYS.REALTIME_DATA, JSON.stringify(realtimeArray))

      console.log('[DataManager] 移除基金:', code)
    }
  }

  removeFunds(codes: string[]) {
    const codeSet = new Set(codes)
    state.fundList = state.fundList.filter(c => !codeSet.has(c))
    localStorage.setItem(STORAGE_KEYS.FUND_LIST, JSON.stringify(state.fundList))
    localStorage.setItem(STORAGE_KEYS.FUND_LIST_DIRTY, 'true')

    for (const code of codes) {
      state.realtimeData.delete(code)
    }

    const realtimeArray = Array.from(state.realtimeData.values())
    localStorage.setItem(STORAGE_KEYS.REALTIME_DATA, JSON.stringify(realtimeArray))

    console.log('[DataManager] 批量移除基金:', codes)
  }

  /**
   * 重置基金列表为默认列表
   * 强制从API获取最新默认基金列表
   */
  async resetFundList(): Promise<string[]> {
    console.log('[DataManager] 重置基金列表为默认列表...')

    // 清除本地存储的基金列表和dirty标记
    localStorage.removeItem(STORAGE_KEYS.FUND_LIST)
    localStorage.removeItem(STORAGE_KEYS.FUND_LIST_DIRTY)

    // 重置状态
    state.fundList = []
    state.fundListLoaded = false

    // 强制从API获取最新列表
    const data = await this.fetchFundListFromAPI()

    // 清空现有实时数据
    state.realtimeData.clear()

    // 重新加载实时数据
    await this.loadRealtimeData(data, true)

    console.log('[DataManager] 基金列表重置完成:', data.length, '只基金')
    return data
  }

  // ============ 实时数据操作 ============

  getRealtimeData(code: string): FundRealtimeData | undefined {
    return state.realtimeData.get(code)
  }

  updateRealtimeItem(item: FundRealtimeData): void {
    state.realtimeData.set(item.code, item)
    state.realtimeLastFetch = Date.now()
    this.saveRealtimeDataToStorage()
  }

  /**
   * 加载实时数据
   */
  async loadRealtimeData(codes?: string[], forceRefresh = false): Promise<FundRealtimeData[]> {
    const targetCodes = codes || state.fundList

    if (targetCodes.length === 0) {
      console.log('[DataManager] 没有基金代码，跳过实时数据加载')
      return []
    }

    const uniqueCodes = [...new Set(targetCodes)]

    // 检查缓存是否有效
    const now = Date.now()
    const timeSinceLastFetch = now - state.realtimeLastFetch
    const cacheValid = !forceRefresh &&
      timeSinceLastFetch < CACHE_TTL.REALTIME &&
      uniqueCodes.every(code => state.realtimeData.has(code))

    if (cacheValid) {
      cacheStats.hits += uniqueCodes.length
      cacheStats.total += uniqueCodes.length
      console.log(`[DataManager] ✅ 缓存命中: ${uniqueCodes.length} 只基金`)
      return uniqueCodes.map(code => state.realtimeData.get(code)!)
    }

    cacheStats.total += uniqueCodes.length
    cacheStats.misses += uniqueCodes.length

    const requestKey = `realtime_${uniqueCodes.sort().join('_')}`
    const pendingRequest = getPendingRequest<FundRealtimeData[]>(requestKey)
    if (pendingRequest) {
      return pendingRequest
    }

    state.realtimeLoading = true
    const request = this.fetchRealtimeDataFromAPI(uniqueCodes)
    setPendingRequest(requestKey, request)

    try {
      const result = await request
      return result
    } finally {
      pendingRequests.delete(requestKey)
      state.realtimeLoading = false
    }
  }

  /**
   * 从本地存储恢复实时数据
   * 策略：始终恢复本地数据，不管是否过期，确保页面刷新后有数据可显示
   */
  private loadRealtimeDataFromStorage(): boolean {
    const stored = localStorage.getItem(STORAGE_KEYS.REALTIME_DATA)
    const timeStored = localStorage.getItem(STORAGE_KEYS.REALTIME_FETCH_TIME)

    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) {
          const dataMap = new Map<string, FundRealtimeData>()
          parsed.forEach((item: FundRealtimeData) => {
            dataMap.set(item.code, item)
          })
          state.realtimeData = dataMap

          // 恢复时间戳（用于判断是否需要刷新）
          if (timeStored) {
            state.realtimeLastFetch = parseInt(timeStored, 10)
          }

          console.log('[DataManager] 从本地存储恢复实时数据:', parsed.length, '只基金')
          return true
        }
      } catch (e) {
        console.warn('[DataManager] 恢复实时数据失败:', e)
      }
    }
    return false
  }

  private async fetchRealtimeDataFromAPI(codes: string[]): Promise<FundRealtimeData[]> {
    try {
      console.log('[DataManager] 从API获取实时数据:', codes.length, '只基金')
      const data = await fundApi.getRealtimeBatch(codes)
      const enrichedData = await this.enrichRealtimeAlternatives(data)

      // 更新内存缓存
      enrichedData.forEach(item => {
        state.realtimeData.set(item.code, item)
      })
      state.realtimeLastFetch = Date.now()
      state.realtimeError = null

      // 保存到本地存储
      this.saveRealtimeDataToStorage()

      console.log('[DataManager] 实时数据加载完成:', enrichedData.length)
      return enrichedData
    } catch (e) {
      console.error('[DataManager] 获取实时数据失败:', e)
      // 只有在没有本地缓存时才设置错误
      if (state.realtimeData.size === 0) {
        state.realtimeError = '获取实时数据失败'
      }
      throw e
    }
  }

  private async enrichRealtimeAlternatives(data: FundRealtimeData[]): Promise<FundRealtimeData[]> {
    const nonRealtimeItems = data.filter(item => item.is_realtime === false)
    if (nonRealtimeItems.length === 0) {
      return data
    }

    const alternativeResults = await Promise.allSettled(
      nonRealtimeItems.map(item => fundApi.getRealtimeAlternatives(item.code, item.name))
    )
    const alternativeMap = new Map<string, RealtimeAlternativeResult>()
    alternativeResults.forEach(result => {
      if (result.status === 'fulfilled' && result.value && !result.value.skipped) {
        alternativeMap.set(result.value.code, result.value)
      }
    })

    return data.map(item => {
      const alternatives = alternativeMap.get(item.code)
      const estimate = alternatives?.holdings_based_estimate
      if (estimate?.feasible && estimate.weighted_stock_change_pct !== null && estimate.weighted_stock_change_pct !== undefined) {
        return {
          ...item,
          estimate_change: estimate.weighted_stock_change_pct,
          update_time: this.formatMinuteTime(new Date()),
          status: '持仓估算',
          data_source: 'holdings_estimate',
          data_source_display_name: '持仓实时估算',
          data_source_short_name: 'Holdings',
          data_source_description: `基于 ${estimate.position_date || '最新披露'} 十大持仓和实时股票行情的加权估算，报价覆盖 ${this.formatPercentRatio(estimate.quoted_weight_coverage)}。`,
          data_kind: 'holdings_estimate',
          data_kind_label: '持仓估算',
          is_realtime: false,
          data_timestamp: new Date().toISOString()
        }
      }

      const reference = alternatives?.reference_symbol_estimate
      if (reference?.feasible && reference.weighted_stock_change_pct !== null && reference.weighted_stock_change_pct !== undefined) {
        return {
          ...item,
          estimate_change: reference.weighted_stock_change_pct,
          update_time: this.formatMinuteTime(new Date()),
          status: '标的估算',
          data_source: 'reference_symbol_estimate',
          data_source_display_name: '引用标的估算',
          data_source_short_name: 'Reference',
          data_source_description: `持仓穿透不足，使用 ${reference.references?.map(ref => ref.name).join('、') || '参考标的'} 行情估算。`,
          data_kind: 'reference_symbol_estimate',
          data_kind_label: '标的估算',
          is_realtime: false,
          data_timestamp: new Date().toISOString()
        }
      }

      const fallback = alternatives?.fallback_estimate
      if (!fallback?.feasible || fallback.change_pct === null || fallback.change_pct === undefined) {
        return item
      }

      return {
        ...item,
        estimate_change: fallback.change_pct,
        update_time: fallback.update_time || item.update_time,
        status: '兜底估算',
        data_source: fallback.source || item.data_source || 'fallback_estimate',
        data_source_display_name: '净值/行情兜底估算',
        data_source_short_name: 'Fallback',
        data_source_description: `持仓穿透不可用，使用${fallback.source === 'tencent' ? '腾讯基金行情' : '最新净值涨跌幅'}作为估算参考。`,
        data_kind: 'fallback_estimate',
        data_kind_label: '兜底估算',
        is_realtime: false,
        data_timestamp: new Date().toISOString()
      }
    })
  }

  private formatMinuteTime(date: Date): string {
    const pad = (value: number) => String(value).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
  }

  private formatPercentRatio(value?: number | null): string {
    if (value === null || value === undefined || isNaN(Number(value))) return '--'
    return `${(Number(value) * 100).toFixed(0)}%`
  }

  /**
   * 保存实时数据到本地存储
   */
  private saveRealtimeDataToStorage(): void {
    try {
      const dataArray = Array.from(state.realtimeData.values())
      localStorage.setItem(STORAGE_KEYS.REALTIME_DATA, JSON.stringify(dataArray))
      localStorage.setItem(STORAGE_KEYS.REALTIME_FETCH_TIME, String(state.realtimeLastFetch))
    } catch (e) {
      console.warn('[DataManager] 保存实时数据到本地存储失败:', e)
    }
  }

  // ============ 持仓数据操作 ============

  /**
   * 加载持仓数据
   */
  async loadPortfolio(forceRefresh = false): Promise<{ items: PortfolioItem[], stats: PortfolioStats }> {
    const now = Date.now()
    const cacheValid = !forceRefresh &&
      state.portfolioLoaded &&
      (now - state.portfolioLastFetch) < CACHE_TTL.PORTFOLIO

    if (cacheValid) {
      console.log('[DataManager] 使用缓存的持仓数据')
      return {
        items: state.portfolioItems,
        stats: state.portfolioStats!
      }
    }

    const requestKey = 'portfolio'
    const pendingRequest = getPendingRequest<PortfolioLoadResult>(requestKey)
    if (pendingRequest) {
      return pendingRequest
    }

    state.portfolioLoading = true
    const request = this.fetchPortfolioFromAPI()
    setPendingRequest(requestKey, request)

    try {
      const result = await request
      return result
    } finally {
      pendingRequests.delete(requestKey)
      state.portfolioLoading = false
    }
  }

  /**
   * 从本地存储恢复持仓数据
   * 策略：始终恢复本地数据，不管是否过期，确保页面刷新后有数据可显示
   */
  private loadPortfolioFromStorage(): boolean {
    const itemsStored = localStorage.getItem(STORAGE_KEYS.PORTFOLIO_ITEMS)
    const statsStored = localStorage.getItem(STORAGE_KEYS.PORTFOLIO_STATS)
    const timeStored = localStorage.getItem(STORAGE_KEYS.PORTFOLIO_FETCH_TIME)

    if (itemsStored) {
      try {
        const items = JSON.parse(itemsStored)

        if (Array.isArray(items) && items.length > 0) {
          // 去重：根据 id 去重
          const uniqueMap = new Map<number, PortfolioItem>()
          items.forEach((item: PortfolioItem) => {
            if (item.id !== undefined) {
              uniqueMap.set(item.id, item)
            } else {
              // 没有id的项，使用 fund_code 作为key
              const existing = Array.from(uniqueMap.values()).find(i => i.fund_code === item.fund_code)
              if (!existing) {
                uniqueMap.set(Date.now() + Math.random(), item)
              }
            }
          })
          const uniqueItems = Array.from(uniqueMap.values())

          // 恢复持仓数据
          state.portfolioItems = uniqueItems
          state.portfolioLoaded = true

          // 恢复统计数据（如果有）
          if (statsStored) {
            const stats = JSON.parse(statsStored)
            // 同步更新 item_count
            if (stats) {
              stats.item_count = uniqueItems.length
            }
            state.portfolioStats = stats
          }

          // 恢复时间戳（用于判断是否需要刷新）
          if (timeStored) {
            state.portfolioLastFetch = parseInt(timeStored, 10)
          }

          console.log('[DataManager] 从本地存储恢复持仓数据:', uniqueItems.length, '条（去重前:', items.length, '条）')
          return true
        }
      } catch (e) {
        console.warn('[DataManager] 恢复持仓数据失败:', e)
      }
    }
    return false
  }

  private async fetchPortfolioFromAPI(): Promise<{ items: PortfolioItem[], stats: PortfolioStats }> {
    try {
      console.log('[DataManager] 从API获取持仓数据...')
      const data = await portfolioApi.getAll()

      // 策略：合并新数据和旧数据，保留已有数据直到新数据有效
      let newItems = data.items || []
      const newStats = data.stats || null

      // 去重：根据 id 去重，保留最新的数据
      if (newItems.length > 0) {
        const uniqueMap = new Map<number, PortfolioItem>()
        newItems.forEach(item => {
          if (item.id !== undefined) {
            // 如果存在重复id，保留最新的（后面的覆盖前面的）
            uniqueMap.set(item.id, item)
          } else {
            // 没有id的项，使用 fund_code 作为key
            const key = item.fund_code
            const existing = Array.from(uniqueMap.values()).find(i => i.fund_code === key)
            if (!existing) {
              uniqueMap.set(Date.now() + Math.random(), item)
            }
          }
        })
        newItems = Array.from(uniqueMap.values())
        console.log('[DataManager] 数据去重后:', newItems.length, '条')
      }

      if (newItems.length > 0) {
        // 新数据有效，完全替换
        state.portfolioItems = newItems
        // 同步更新 stats 中的 item_count，确保一致性
        if (newStats) {
          newStats.item_count = newItems.length
        }
        state.portfolioStats = newStats
        console.log('[DataManager] 使用API新数据:', newItems.length, '条')
      } else if (state.portfolioItems.length > 0) {
        // API返回空但本地有数据，保留本地数据（不清空）
        console.log('[DataManager] API返回空数据，保留本地缓存:', state.portfolioItems.length, '条')
        // 保持原有数据不变，不执行任何清空操作
      } else {
        // 都为空，设置为空
        state.portfolioItems = []
        state.portfolioStats = null
      }

      // 清除错误状态
      state.portfolioError = null
      
      state.portfolioLoaded = true
      state.portfolioLastFetch = Date.now()

      // 保存到本地存储
      this.savePortfolioToStorage()

      // 加载缺失的实时数据（仅在已有数据基础上补充）
      if (state.portfolioItems.length > 0) {
        const missingCodes = state.portfolioItems
          .map(item => item.fund_code)
          .filter(code => !state.realtimeData.has(code))

        if (missingCodes.length > 0) {
          this.loadRealtimeData(missingCodes).catch(e => {
            console.warn('[DataManager] 加载持仓基金实时数据失败:', e)
          })
        }
      }

      console.log('[DataManager] 持仓数据加载完成:', state.portfolioItems.length)

      return {
        items: state.portfolioItems,
        stats: state.portfolioStats!
      }
    } catch (e) {
      console.error('[DataManager] 获取持仓数据失败:', e)
      // 只有在没有本地缓存时才设置错误
      if (state.portfolioItems.length === 0) {
        state.portfolioError = '获取持仓数据失败'
      }
      // 出错时不清空已有数据
      throw e
    }
  }

  /**
   * 保存持仓数据到本地存储
   */
  private savePortfolioToStorage(): void {
    try {
      localStorage.setItem(STORAGE_KEYS.PORTFOLIO_ITEMS, JSON.stringify(state.portfolioItems))
      localStorage.setItem(STORAGE_KEYS.PORTFOLIO_STATS, JSON.stringify(state.portfolioStats))
      localStorage.setItem(STORAGE_KEYS.PORTFOLIO_FETCH_TIME, String(state.portfolioLastFetch))
    } catch (e) {
      console.warn('[DataManager] 保存持仓数据到本地存储失败:', e)
    }
  }

  async refreshPortfolio(): Promise<void> {
    console.log('[DataManager] 刷新持仓数据...')
    await this.loadPortfolio(true)
  }

  // ============ 批量操作 ============

  async refreshAll(): Promise<void> {
    console.log('[DataManager] 刷新所有数据...')

    try {
      await this.loadPortfolio(true)

      if (state.fundList.length > 0) {
        await this.loadRealtimeData(state.fundList, true)
      }

      console.log('[DataManager] 所有数据刷新完成')
    } catch (e) {
      console.error('[DataManager] 刷新数据失败:', e)
      throw e
    }
  }

  // ============ 工具方法 ============

  getCacheStats() {
    return {
      ...cacheStats,
      hitRate: cacheStats.total > 0 ? (cacheStats.hits / cacheStats.total * 100) : 0
    }
  }

  clearCache(): void {
    state.realtimeData.clear()
    state.realtimeLastFetch = 0
    state.portfolioLastFetch = 0
    cacheStats.hits = 0
    cacheStats.misses = 0
    cacheStats.total = 0

    // 清除本地存储
    Object.values(STORAGE_KEYS).forEach(key => {
      localStorage.removeItem(key)
    })
    // 同时清除dirty标记
    localStorage.removeItem(STORAGE_KEYS.FUND_LIST_DIRTY)

    console.log('[DataManager] 缓存已清除')
  }

  clearError(): void {
    state.fundListError = null
    state.realtimeError = null
    state.portfolioError = null
  }

  clearPortfolioError(): void {
    state.portfolioError = null
  }

  getState() {
    return state
  }

  /**
   * 更新持仓列表（用于乐观更新）
   */
  updatePortfolioItems(items: PortfolioItem[]): void {
    state.portfolioItems = items
    // 重新计算统计数据
    this.calculatePortfolioStats()
    // 保存到本地存储
    localStorage.setItem(STORAGE_KEYS.PORTFOLIO_ITEMS, JSON.stringify(items))
  }

  /**
   * 计算持仓统计数据
   */
  private calculatePortfolioStats(): void {
    const items = state.portfolioItems
    if (items.length === 0) {
      state.portfolioStats = {
        total_value: 0,
        total_cost: 0,
        total_profit_loss: 0,
        total_profit_loss_pct: 0,
        item_count: 0
      }
      return
    }

    // 确保所有数值都是数字类型
    const totalCost = items.reduce((sum, item) => {
      const cost = typeof item.cost_amount === 'string' ? parseFloat(item.cost_amount) : Number(item.cost_amount)
      return sum + (isNaN(cost) ? 0 : cost)
    }, 0)
    
    const totalValue = items.reduce((sum, item) => {
      // 优先使用 current_value，如果没有则使用 cost_amount（乐观更新时）
      let current = typeof item.current_value === 'string' ? parseFloat(item.current_value) : Number(item.current_value)
      if (isNaN(current) || current === 0) {
        // 如果没有 current_value，尝试用 current_nav * hold_shares 计算
        const nav = typeof item.current_nav === 'string' ? parseFloat(item.current_nav) : Number(item.current_nav)
        const shares = typeof item.hold_shares === 'string' ? parseFloat(item.hold_shares) : Number(item.hold_shares)
        if (!isNaN(nav) && !isNaN(shares) && nav > 0 && shares > 0) {
          current = nav * shares
        } else {
          // 如果都没有，使用成本价
          const cost = typeof item.cost_amount === 'string' ? parseFloat(item.cost_amount) : Number(item.cost_amount)
          current = isNaN(cost) ? 0 : cost
        }
      }
      return sum + current
    }, 0)
    
    const totalProfitLoss = totalValue - totalCost
    const totalProfitLossPct = totalCost > 0 ? (totalProfitLoss / totalCost) * 100 : 0

    state.portfolioStats = {
      total_value: totalValue,
      total_cost: totalCost,
      total_profit_loss: totalProfitLoss,
      total_profit_loss_pct: totalProfitLossPct,
      item_count: items.length
    }

    // 保存到本地存储
    localStorage.setItem(STORAGE_KEYS.PORTFOLIO_STATS, JSON.stringify(state.portfolioStats))
  }
}

export const dataManager = new DataManager()
export default dataManager
