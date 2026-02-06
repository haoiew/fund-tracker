import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { dataManager } from './dataManager'
import portfolioApi, { type PortfolioItem, type PortfolioStats } from '@/api/portfolio'
import { ElMessage } from 'element-plus'

export const usePortfolioStore = defineStore('portfolio', () => {
  // ============ State (从 DataManager 获取) ============

  /**
   * 持仓列表（自动关联实时数据）
  */
  const items = dataManager.getPortfolioWithRealtime

  /**
   * 持仓统计
   */
  const stats = dataManager.getPortfolioStats

  /**
   * 是否已初始化
   */
  const initialized = dataManager.isPortfolioLoaded

  /**
   * 本地持仓列表（用于乐观更新）
   */
  const localItems = ref<PortfolioItem[]>([])

  // ============ Getters (计算属性) ============

  /**
   * 加载状态
   */
  const loading = computed(() => dataManager.getState().portfolioLoading)

  /**
   * 错误信息
   */
  const error = computed(() => dataManager.getState().error)

  /**
   * 持仓数量
   */
  const itemCount = computed(() => items.value.length)

  /**
   * 总市值
   */
  const totalValue = computed(() => stats.value?.total_value || 0)

  /**
   * 总盈亏
   */
  const totalProfit = computed(() => stats.value?.total_profit_loss || 0)

  /**
   * 总收益率
   */
  const totalProfitPct = computed(() => stats.value?.total_profit_loss_pct || 0)

  /**
   * 是否盈利
   */
  const profitPositive = computed(() => totalProfit.value >= 0)

  /**
   * 是否有数据
   */
  const hasData = computed(() => items.value.length > 0)

  // ============ Actions ============

  /**
   * 获取持仓数据
   * 从 DataManager 加载，自动处理缓存和实时数据关联
   */
  async function fetchPortfolio(): Promise<void> {
    await dataManager.loadPortfolio()
  }

  /**
   * 刷新持仓数据
   */
  async function refreshPortfolio(): Promise<void> {
    await dataManager.refreshPortfolio()
  }

  /**
   * 添加持仓（带乐观更新 - 秒级响应）
   */
  async function addItem(data: {
    fund_code: string
    fund_name?: string
    hold_shares?: number
    cost_amount?: number
    cost_nav?: number
    buy_date?: string
    remark?: string
  }): Promise<boolean> {
    // 乐观更新：立即添加到本地列表（秒级响应）
    const tempItem: PortfolioItem = {
      id: Date.now(), // 临时ID
      fund_code: data.fund_code,
      fund_name: data.fund_name || data.fund_code,
      hold_shares: data.hold_shares || 0,
      cost_amount: data.cost_amount || 0,
      cost_nav: data.cost_nav,
      current_nav: data.cost_nav,
      current_value: (data.cost_nav || 0) * (data.hold_shares || 0),
      profit_amount: 0,
      profit_rate: 0,
      buy_date: data.buy_date,
      remark: data.remark,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    // 立即更新本地状态（使用新数组触发响应式更新）
    const currentItems = [...dataManager.getState().portfolioItems, tempItem]
    dataManager.updatePortfolioItems(currentItems)

    // 异步API调用（不等待，后台执行）
    portfolioApi.add({
      fund_code: data.fund_code,
      fund_name: data.fund_name,
      hold_shares: data.hold_shares || 0,
      cost_amount: data.cost_amount || 0,
      cost_nav: data.cost_nav,
      buy_date: data.buy_date,
      remark: data.remark
    }).then(() => {
      // API成功后刷新数据获取真实ID
      dataManager.refreshPortfolio()
    }).catch(e => {
      console.error('添加API调用失败:', e)
      // API失败时回滚
      dataManager.refreshPortfolio()
    })

    return true
  }

  /**
   * 更新持仓（带乐观更新 - 秒级响应）
   */
  async function updateItem(id: number, data: {
    fund_code?: string
    fund_name?: string
    hold_shares?: number
    cost_amount?: number
    cost_nav?: number
    buy_date?: string
    remark?: string
  }): Promise<boolean> {
    // 乐观更新：立即更新本地列表（秒级响应）
    const currentItems = dataManager.getState().portfolioItems.map(item => {
      if (item.id === id) {
        return {
          ...item,
          ...data,
          updated_at: new Date().toISOString()
        }
      }
      return item
    })
    dataManager.updatePortfolioItems(currentItems)

    // 异步API调用（不等待，后台执行）
    portfolioApi.update(id, {
      hold_shares: data.hold_shares,
      cost_amount: data.cost_amount,
      cost_nav: data.cost_nav,
      buy_date: data.buy_date,
      remark: data.remark
    }).catch(e => {
      console.error('更新API调用失败:', e)
      // API失败时回滚，从服务器重新获取数据
      dataManager.refreshPortfolio()
    })

    return true
  }

  /**
   * 删除持仓（带乐观更新）
   */
  async function deleteItem(id: number): Promise<boolean> {
    try {
      // 乐观更新：立即从本地列表移除（使用新数组触发响应式更新）
      const currentItems = dataManager.getState().portfolioItems.filter(item => item.id !== id)
      dataManager.updatePortfolioItems(currentItems)

      // 异步API调用（不等待）
      portfolioApi.delete(id).catch(e => {
        console.error('删除API调用失败:', e)
        // API失败时回滚，从服务器重新获取数据
        dataManager.refreshPortfolio()
      })

      return true
    } catch (e) {
      console.error('删除失败:', e)
      // 失败时回滚
      await dataManager.refreshPortfolio()
      return false
    }
  }

  /**
   * 清除错误
   */
  function clearError(): void {
    dataManager.clearError()
  }

  return {
    // State
    items,
    stats,
    initialized,
    loading,
    error,

    // Getters
    itemCount,
    totalValue,
    totalProfit,
    totalProfitPct,
    profitPositive,
    hasData,

    // Actions
    fetchPortfolio,
    refreshPortfolio,
    addItem,
    updateItem,
    deleteItem,
    clearError
  }
})
