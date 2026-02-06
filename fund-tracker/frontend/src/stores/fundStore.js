// 基金数据状态管理
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fundApi } from '../api/fund.js'

export const useFundStore = defineStore('fund', () => {
  // State
  const fundList = ref([])
  const realtimeData = ref({})
  const historyData = ref({})
  const loading = ref(false)
  
  // Getters
  const upFunds = computed(() => {
    return Object.values(realtimeData.value).filter(f => f.estimate_change > 0)
  })
  
  const downFunds = computed(() => {
    return Object.values(realtimeData.value).filter(f => f.estimate_change < 0)
  })
  
  // Actions
  const fetchRealtimeData = async (codes) => {
    loading.value = true
    try {
      const res = await fundApi.getRealtimeBatch(codes)
      if (res.code === 200) {
        // 清除旧数据，避免缓存问题
        realtimeData.value = {}
        res.data.forEach(fund => {
          realtimeData.value[fund.code] = fund
        })
      }
    } catch (error) {
      console.error('获取实时数据失败:', error)
    } finally {
      loading.value = false
    }
  }
  
  const fetchHistoryData = async (code, range = '3M') => {
    try {
      const res = await fundApi.getHistory(code, range)
      if (res.code === 200) {
        historyData.value[code] = res.data
      }
    } catch (error) {
      console.error('获取历史数据失败:', error)
    }
  }
  
  const searchFunds = async (keyword) => {
    try {
      const res = await fundApi.search(keyword)
      if (res.code === 200) {
        return res.data
      }
    } catch (error) {
      console.error('搜索基金失败:', error)
    }
    return []
  }
  
  return {
    fundList,
    realtimeData,
    historyData,
    loading,
    upFunds,
    downFunds,
    fetchRealtimeData,
    fetchHistoryData,
    searchFunds
  }
})
