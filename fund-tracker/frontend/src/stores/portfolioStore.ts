import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { dataManager } from './dataManager'
import portfolioApi, { type PortfolioItem } from '@/api/portfolio'
import { ElMessage } from 'element-plus'

type PortfolioAddInput = {
  fund_code: string
  fund_name?: string
  hold_shares?: number
  cost_amount?: number
  cost_nav?: number
  buy_date?: string
  remark?: string
}

type PortfolioCreatePayload = Omit<PortfolioItem, 'id' | 'created_at' | 'updated_at'>

type PortfolioUpdateInput = {
  hold_shares?: number
  cost_amount?: number
  cost_nav?: number
  buy_date?: string
  remark?: string
}

type PendingOperationBase = {
  id: string
  status: 'pending' | 'success' | 'error'
  retryCount: number
  maxRetries: number
}

type PendingOperation =
  | (PendingOperationBase & {
      type: 'add'
      data: { tempItem: PortfolioItem; apiData: PortfolioAddInput }
    })
  | (PendingOperationBase & {
      type: 'update'
      data: { id: number; originalItem: PortfolioItem; newData: PortfolioUpdateInput }
    })
  | (PendingOperationBase & {
      type: 'delete'
      data: { id: number; originalItem: PortfolioItem }
    })

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function toPortfolioCreatePayload(data: PortfolioAddInput): PortfolioCreatePayload {
  return {
    fund_code: data.fund_code,
    fund_name: data.fund_name,
    hold_shares: data.hold_shares || 0,
    cost_amount: data.cost_amount || 0,
    cost_nav: data.cost_nav,
    buy_date: data.buy_date,
    remark: data.remark
  }
}

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
   * 待处理操作队列
   */
  const pendingOperations = ref<Map<string, PendingOperation>>(new Map())

  /**
   * 是否正在同步
   */
  const isSyncing = ref(false)

  // ============ Getters (计算属性) ============

  /**
   * 加载状态
   */
  const loading = computed(() => dataManager.getState().portfolioLoading)

  /**
   * 错误信息（持仓专用）
   */
  const error = computed(() => dataManager.getState().portfolioError)

  /**
   * 持仓数量
   */
  const itemCount = computed(() => items.value.length)

  /**
   * 总市值
   */
  const totalValue = computed(() => stats.value?.total_value || 0)

  /**
   * 持有收益
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

  /**
   * 是否有未完成的操作
   */
  const hasPendingOperations = computed(() => {
    return Array.from(pendingOperations.value.values()).some(
      op => op.status === 'pending'
    )
  })

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
   * 生成操作ID
   */
  function generateOperationId(): string {
    return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * 添加持仓（带乐观更新和确认机制）
   */
  async function addItem(data: PortfolioAddInput): Promise<boolean> {
    const operationId = generateOperationId()

    // 创建乐观更新项
    const tempItem: PortfolioItem = {
      id: Date.now() + Math.floor(Math.random() * 1000), // 临时ID（避免碰撞）
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

    // 添加到待处理队列
    pendingOperations.value.set(operationId, {
      id: operationId,
      type: 'add',
      data: { tempItem, apiData: data },
      status: 'pending',
      retryCount: 0,
      maxRetries: 3
    })

    // 乐观更新：立即显示在UI上
    const currentItems = [...dataManager.getState().portfolioItems, tempItem]
    dataManager.updatePortfolioItems(currentItems)

    try {
      // 调用API
      await portfolioApi.add(toPortfolioCreatePayload(data))

      // 更新操作状态为成功
      const operation = pendingOperations.value.get(operationId)
      if (operation) {
        operation.status = 'success'
      }

      // 刷新数据获取真实ID和完整数据
      await dataManager.refreshPortfolio()

      ElMessage.success('添加成功')
      return true

    } catch (e: unknown) {
      console.error('添加持仓失败:', e)

      // 更新操作状态为错误
      const operation = pendingOperations.value.get(operationId)
      if (operation) {
        operation.status = 'error'
      }

      // 回滚乐观更新
      await dataManager.refreshPortfolio()

      ElMessage.error(getErrorMessage(e, '添加失败'))
      return false

    } finally {
      // 清理已完成的操作
      setTimeout(() => {
        pendingOperations.value.delete(operationId)
      }, 5000)
    }
  }

  /**
   * 批量添加持仓（优化性能）
   */
  async function batchAddItems(items: PortfolioAddInput[]): Promise<{ success: number; failed: number }> {
    let success = 0
    let failed = 0

    // 乐观更新：先显示所有项
    const tempItems: PortfolioItem[] = items.map((data, index) => ({
      id: Date.now() + Math.floor(Math.random() * 1000) + index,
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
    }))

    const currentItems = [...dataManager.getState().portfolioItems, ...tempItems]
    dataManager.updatePortfolioItems(currentItems)

    // 顺序执行API调用（避免并发问题）
    for (const data of items) {
      try {
        await portfolioApi.add(toPortfolioCreatePayload(data))
        success++
      } catch (e) {
        console.error(`添加 ${data.fund_code} 失败:`, e)
        failed++
      }
    }

    // 刷新数据获取真实ID
    await dataManager.refreshPortfolio()

    if (failed === 0) {
      ElMessage.success(`成功添加 ${success} 只基金`)
    } else {
      ElMessage.warning(`添加完成：成功 ${success} 只，失败 ${failed} 只`)
    }

    return { success, failed }
  }

  /**
   * 更新持仓（带乐观更新和确认机制）
   */
  async function updateItem(id: number, data: PortfolioUpdateInput): Promise<boolean> {
    const operationId = generateOperationId()

    // 保存原始数据用于回滚
    const originalItem = dataManager.getState().portfolioItems.find(item => item.id === id)
    if (!originalItem) {
      ElMessage.error('持仓不存在')
      return false
    }

    // 添加到待处理队列
    pendingOperations.value.set(operationId, {
      id: operationId,
      type: 'update',
      data: { id, originalItem, newData: data },
      status: 'pending',
      retryCount: 0,
      maxRetries: 3
    })

    // 乐观更新
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

    try {
      await portfolioApi.update(id, {
        hold_shares: data.hold_shares,
        cost_amount: data.cost_amount,
        cost_nav: data.cost_nav,
        buy_date: data.buy_date,
        remark: data.remark
      })

      // 更新操作状态
      const operation = pendingOperations.value.get(operationId)
      if (operation) {
        operation.status = 'success'
      }

      // 刷新数据
      await dataManager.refreshPortfolio()

      ElMessage.success('更新成功')
      return true

    } catch (e: unknown) {
      console.error('更新持仓失败:', e)

      // 更新操作状态
      const operation = pendingOperations.value.get(operationId)
      if (operation) {
        operation.status = 'error'
      }

      // 回滚
      await dataManager.refreshPortfolio()

      ElMessage.error(getErrorMessage(e, '更新失败'))
      return false

    } finally {
      setTimeout(() => {
        pendingOperations.value.delete(operationId)
      }, 5000)
    }
  }

  /**
   * 删除持仓（带乐观更新和确认机制）
   */
  async function deleteItem(id: number): Promise<boolean> {
    const operationId = generateOperationId()

    // 保存原始数据用于回滚
    const originalItem = dataManager.getState().portfolioItems.find(item => item.id === id)
    if (!originalItem) {
      ElMessage.error('持仓不存在')
      return false
    }

    // 添加到待处理队列
    pendingOperations.value.set(operationId, {
      id: operationId,
      type: 'delete',
      data: { id, originalItem },
      status: 'pending',
      retryCount: 0,
      maxRetries: 3
    })

    // 乐观更新：立即移除
    const currentItems = dataManager.getState().portfolioItems.filter(item => item.id !== id)
    dataManager.updatePortfolioItems(currentItems)

    try {
      await portfolioApi.delete(id)

      // 更新操作状态
      const operation = pendingOperations.value.get(operationId)
      if (operation) {
        operation.status = 'success'
      }

      // 刷新数据
      await dataManager.refreshPortfolio()

      return true

    } catch (e: unknown) {
      console.error('删除持仓失败:', e)

      // 更新操作状态
      const operation = pendingOperations.value.get(operationId)
      if (operation) {
        operation.status = 'error'
      }

      // 回滚：恢复原始数据
      await dataManager.refreshPortfolio()

      ElMessage.error(getErrorMessage(e, '删除失败'))
      return false

    } finally {
      setTimeout(() => {
        pendingOperations.value.delete(operationId)
      }, 5000)
    }
  }

  /**
   * 同步所有待处理操作
   */
  async function syncPendingOperations(): Promise<void> {
    if (isSyncing.value) return

    isSyncing.value = true
    try {
      const pending = Array.from(pendingOperations.value.values())
        .filter(op => op.status === 'pending')

      for (const operation of pending) {
        if (operation.retryCount >= operation.maxRetries) {
          operation.status = 'error'
          continue
        }

        operation.retryCount++

        try {
          switch (operation.type) {
            case 'add':
              await portfolioApi.add(toPortfolioCreatePayload(operation.data.apiData))
              break
            case 'update':
              await portfolioApi.update(operation.data.id, operation.data.newData)
              break
            case 'delete':
              await portfolioApi.delete(operation.data.id)
              break
          }
          operation.status = 'success'
        } catch (e) {
          console.error(`同步操作失败 ${operation.id}:`, e)
        }
      }

      // 刷新数据
      await dataManager.refreshPortfolio()

    } finally {
      isSyncing.value = false
    }
  }

  /**
   * 清除错误
   */
  function clearError(): void {
    dataManager.clearPortfolioError()
  }

  /**
   * 获取待处理操作列表
   */
  function getPendingOperations(): PendingOperation[] {
    return Array.from(pendingOperations.value.values())
  }

  return {
    // State
    items,
    stats,
    initialized,
    pendingOperations,
    isSyncing,
    loading,
    error,

    // Getters
    itemCount,
    totalValue,
    totalProfit,
    totalProfitPct,
    profitPositive,
    hasData,
    hasPendingOperations,

    // Actions
    fetchPortfolio,
    refreshPortfolio,
    addItem,
    batchAddItems,
    updateItem,
    deleteItem,
    syncPendingOperations,
    clearError,
    getPendingOperations
  }
})
