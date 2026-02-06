<template>
  <div class="fund-chart">
    <div class="chart-header">
      <h3>{{ name }} ({{ code }})</h3>
      <el-radio-group v-model="timeRange" size="small" @change="loadData">
        <el-radio-button value="1W">1周</el-radio-button>
        <el-radio-button value="1M">1月</el-radio-button>
        <el-radio-button value="3M">3月</el-radio-button>
        <el-radio-button value="6M">6月</el-radio-button>
        <el-radio-button value="1Y">1年</el-radio-button>
      </el-radio-group>
    </div>
    <div v-show="loading" class="chart-loading">
      <el-icon class="is-loading" size="32"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <div v-show="!loading" ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import fundApi from '@/api/fund'

const props = defineProps<{
  code: string
  name: string
}>()

const chartRef = ref<HTMLElement>()
const timeRange = ref('3M')
const loading = ref(false)
let chart: echarts.ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return
  
  if (chart) {
    chart.dispose()
  }
  
  chart = echarts.init(chartRef.value)
  window.addEventListener('resize', handleResize)
}

const handleResize = () => {
  chart?.resize()
}

const loadData = async () => {
  loading.value = true

  try {
    // 确保图表已初始化
    if (!chart) {
      await nextTick()
      initChart()
    }

    if (!chart || !chartRef.value) {
      console.error('图表容器未准备好')
      ElMessage.error('图表容器未准备好')
      loading.value = false
      return
    }

    const response = await fundApi.getHistory(props.code, timeRange.value)

    // 提取实际数据（API返回嵌套结构: { data: FundChartData, source: string, updating: boolean }）
    const data = response?.data

    // 检查数据有效性
    if (!data || !Array.isArray(data.dates) || data.dates.length === 0) {
      console.warn('图表数据为空:', data)
      loading.value = false
      return
    }
    
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
    
    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'axis',
        backgroundColor: isDark ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.95)',
        borderColor: isDark ? '#334155' : '#e5e7eb',
        borderWidth: 1,
        textStyle: { color: isDark ? '#f1f5f9' : '#374151' },
        formatter: (params: unknown) => {
          const p = params as { name: string; value?: number }
          return `${p.name}<br/>净值: ${p.value?.toFixed(4) || '--'}`
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: data.dates,
        axisLine: { lineStyle: { color: isDark ? '#334155' : '#e5e7eb' } },
        axisLabel: { color: isDark ? '#94a3b8' : '#6b7280' }
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLine: { show: false },
        splitLine: { lineStyle: { color: isDark ? '#334155' : '#f3f4f6' } },
        axisLabel: { color: isDark ? '#94a3b8' : '#6b7280' }
      },
      series: [{
        name: '净值',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 3,
          color: '#6366f1'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(99, 102, 241, 0.3)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0.05)' }
          ])
        },
        data: data.values
      }]
    }
    
    chart.setOption(option, true)
  } catch (e) {
    console.error('加载图表数据失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // 等待DOM渲染完成
  await nextTick()
  initChart()
  loadData()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})

watch(() => props.code, () => {
  loadData()
})
</script>

<style scoped lang="scss">
.fund-chart {
  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
    }
  }
  
  .chart-loading {
    height: 400px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: var(--text-secondary);
  }
  
  .chart-container {
    height: 400px;
  }
}
</style>
