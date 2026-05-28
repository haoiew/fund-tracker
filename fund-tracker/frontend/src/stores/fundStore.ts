import { defineStore } from 'pinia'
import { computed } from 'vue'
import { dataManager } from './dataManager'
import fundApi, { type FundRealtimeData, type FundTrendResult } from '@/api/fund'

export const useFundStore = defineStore('fund', () => {
  // ============ State (从 DataManager 获取) ============

  /**
   * 基金代码列表
   */
  const fundList = dataManager.getFundList

  /**
   * 是否已初始化
   */
  const initialized = dataManager.isFundListLoaded

  /**
   * 实时数据
   */
  const realtimeData = dataManager.getAllRealtimeData

  // ============ Getters (计算属性) ============

  /**
   * 加载状态
   */
  const loading = computed(() => {
    const state = dataManager.getState()
    return state.fundListLoading || state.realtimeLoading
  })

  /**
   * 错误信息（基金列表或实时数据错误）
   */
  const error = computed(() => {
    const state = dataManager.getState()
    return state.fundListError || state.realtimeError
  })

  /**
   * 是否有数据
   */
  const hasData = computed(() => realtimeData.value.length > 0)

  /**
   * 上涨基金列表
   */
  const upFunds = computed(() =>
    realtimeData.value.filter(f => (f.estimate_change || 0) > 0)
  )

  /**
   * 下跌基金列表
   */
  const downFunds = computed(() =>
    realtimeData.value.filter(f => (f.estimate_change || 0) < 0)
  )

  /**
   * 总涨跌幅
   */
  const totalChange = computed(() => {
    if (realtimeData.value.length === 0) return 0
    const sum = realtimeData.value.reduce((acc, f) => acc + (f.estimate_change || 0), 0)
    return sum / realtimeData.value.length
  })

  /**
   * 获取指定基金的实时数据
   */
  function getFundRealtimeData(code: string): FundRealtimeData | undefined {
    return dataManager.getRealtimeData(code)
  }

  function getFundByName(name: string): { code: string; name: string } | undefined {
    const keyword = name.trim()
    if (!keyword) return undefined
    const found = realtimeData.value.find(f => f.name === keyword || f.name.includes(keyword) || keyword.includes(f.name))
    return found ? { code: found.code, name: found.name } : undefined
  }

  // ============ Actions ============

  /**
   * 初始化基金列表
   * 从 DataManager 加载，避免重复请求
   */
  async function initFundList(): Promise<void> {
    await dataManager.loadFundList()
  }

  /**
   * 获取实时数据
   * 从 DataManager 加载，自动处理缓存
   */
  async function fetchRealtimeData(codes?: string[]): Promise<void> {
    await dataManager.loadRealtimeData(codes)
  }

  /**
   * 添加基金
   */
  function addFund(code: string): void {
    dataManager.addFund(code)
  }

  /**
   * 移除基金
   */
  function removeFund(code: string): void {
    dataManager.removeFund(code)
  }

  /**
   * 筛选基金
   * 不复用实时数据，直接调用API进行筛选
   */
  async function screenFunds(
    direction: 'up' | 'down',
    codes: string[],
    minDays: number,
    minPct: number
  ): Promise<FundTrendResult[]> {
    // 直接调用API进行筛选，不预加载实时数据
    const result = await fundApi.screen(direction, minDays, minPct, codes)
    return result.funds
  }

  /**
   * 获取历史数据
   */
  async function getHistory(code: string, range: string) {
    return await fundApi.getHistory(code, range)
  }

  /**
   * 对比基金
   */
  async function compareFunds(codes: string[], range: string, includeBenchmark = true) {
    // 直接调用API进行对比，不预加载实时数据
    return await fundApi.compare(codes, range, includeBenchmark)
  }

  /**
   * 搜索基金
   */
  async function searchFunds(keyword: string, limit = 10) {
    return await fundApi.search(keyword, limit)
  }

  /**
   * 清除错误
   */
  function clearError(): void {
    dataManager.clearError()
  }

  /**
   * 重置为默认基金列表
   * 清除本地缓存，从API获取最新默认列表
   */
  async function resetToDefault(): Promise<void> {
    await dataManager.resetFundList()
  }

  return {
    // State
    fundList,
    realtimeData,
    initialized,
    loading,
    error,

    // Getters
    hasData,
    upFunds,
    downFunds,
    totalChange,
    getFundRealtimeData,
    getFundByName,

    // Actions
    initFundList,
    fetchRealtimeData,
    addFund,
    removeFund,
    screenFunds,
    getHistory,
    compareFunds,
    searchFunds,
    clearError,
    resetToDefault
  }
})
