// 持仓状态管理
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { portfolioApi } from '../api/portfolio.js'

export const usePortfolioStore = defineStore('portfolio', () => {
  // State
  const portfolios = ref([])
  const profitSummary = ref(null)
  const loading = ref(false)
  
  // Getters
  const totalCost = computed(() => {
    return profitSummary.value?.total_cost || 0
  })
  
  const totalValue = computed(() => {
    return profitSummary.value?.total_value || 0
  })
  
  const totalProfit = computed(() => {
    return profitSummary.value?.total_profit || 0
  })
  
  const profitRate = computed(() => {
    return profitSummary.value?.total_profit_rate || 0
  })
  
  // Actions
  const fetchPortfolios = async () => {
    loading.value = true
    try {
      const res = await portfolioApi.getList()
      if (res.code === 200) {
        portfolios.value = res.data
      }
    } catch (error) {
      console.error('获取持仓失败:', error)
    } finally {
      loading.value = false
    }
  }
  
  const fetchProfit = async () => {
    try {
      const res = await portfolioApi.getProfit()
      if (res.code === 200) {
        profitSummary.value = res.data.summary
      }
    } catch (error) {
      console.error('获取收益失败:', error)
    }
  }
  
  const addPortfolio = async (data) => {
    try {
      const res = await portfolioApi.add(data)
      if (res.code === 200) {
        await fetchPortfolios()
        return true
      }
    } catch (error) {
      console.error('添加持仓失败:', error)
    }
    return false
  }
  
  const deletePortfolio = async (id) => {
    try {
      const res = await portfolioApi.delete(id)
      if (res.code === 200) {
        await fetchPortfolios()
        return true
      }
    } catch (error) {
      console.error('删除持仓失败:', error)
    }
    return false
  }
  
  return {
    portfolios,
    profitSummary,
    loading,
    totalCost,
    totalValue,
    totalProfit,
    profitRate,
    fetchPortfolios,
    fetchProfit,
    addPortfolio,
    deletePortfolio
  }
})
