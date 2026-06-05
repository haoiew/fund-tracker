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
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import fundApi from '@/api/fund'

const props = withDefaults(defineProps<{
  code: string
  name: string
  defaultRange?: string
}>(), {
  defaultRange: '3M'
})

const chartRef = ref<HTMLElement>()
const timeRange = ref(props.defaultRange)
const loading = ref(false)
let chart: echarts.ECharts | null = null

// 金融专业配色方案
const financialColors = {
  // 主色调 - 深蓝（专业稳重）
  primary: '#1e3a8a',
  primaryLight: '#3b82f6',
  // 辅助色
  secondary: '#0f766e',
  accent: '#b45309',
  // 涨跌色
  up: '#dc2626',    // 中国红（上涨）
  down: '#16a34a',  // 中国绿（下跌）
  // 中性色
  neutral: '#64748b',
  // 渐变
  gradientStart: 'rgba(30, 58, 138, 0.4)',
  gradientEnd: 'rgba(30, 58, 138, 0.05)'
}

// 深色主题配色
const darkColors = {
  primary: '#60a5fa',
  primaryLight: '#93c5fd',
  up: '#f87171',
  down: '#4ade80',
  neutral: '#94a3b8',
  gradientStart: 'rgba(96, 165, 250, 0.4)',
  gradientEnd: 'rgba(96, 165, 250, 0.05)'
}

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

// 计算每日涨跌幅
const calculateDailyChanges = (values: number[]): number[] => {
  const changes: number[] = []
  for (let i = 0; i < values.length; i++) {
    if (i === 0) {
      changes.push(0)
    } else {
      const prevValue = values[i - 1] ?? 0
      const currValue = values[i] ?? prevValue
      const change = prevValue > 0 ? ((currValue - prevValue) / prevValue) * 100 : 0
      changes.push(change)
    }
  }
  return changes
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
    const colors = isDark ? darkColors : financialColors
    
    // 计算每日涨跌幅
    const dailyChanges = calculateDailyChanges(data.values)
    
    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'line',
          lineStyle: {
            color: isDark ? '#475569' : '#94a3b8',
            width: 1,
            type: 'dashed'
          }
        },
        backgroundColor: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.98)',
        borderColor: isDark ? '#334155' : '#e2e8f0',
        borderWidth: 1,
        padding: [12, 16],
        textStyle: { 
          color: isDark ? '#f8fafc' : '#1e293b',
          fontSize: 13
        },
        extraCssText: 'box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); border-radius: 8px;',
        formatter: (params: any) => {
          if (!params || !Array.isArray(params) || params.length === 0) {
            return ''
          }
          
          const p = params[0]
          const date = p.name || p.axisValue || '--'
          const dataIndex = p.dataIndex
          
          if (dataIndex === undefined || dataIndex < 0 || dataIndex >= data.values.length) {
            return `<div style="font-weight: 600;">${date}</div>`
          }
          
          const nav = data.values[dataIndex]
          const change = dailyChanges[dataIndex] ?? 0
          const changeColor = change >= 0 ? colors.up : colors.down
          const changeSign = change >= 0 ? '+' : ''
          
          const navStr = nav !== undefined && nav !== null ? nav.toFixed(4) : '--'
          const changeStr = change !== undefined && change !== null ? change.toFixed(2) : '0.00'
          
          return `
            <div style="font-weight: 600; margin-bottom: 8px; color: ${isDark ? '#f8fafc' : '#1e293b'};">${date}</div>
            <div style="display: flex; justify-content: space-between; gap: 20px; margin-bottom: 4px;">
              <span style="color: ${isDark ? '#94a3b8' : '#64748b'};">单位净值</span>
              <span style="font-weight: 600; font-family: 'Roboto Mono', monospace;">${navStr}</span>
            </div>
            <div style="display: flex; justify-content: space-between; gap: 20px;">
              <span style="color: ${isDark ? '#94a3b8' : '#64748b'};">日涨跌幅</span>
              <span style="font-weight: 600; color: ${changeColor}; font-family: 'Roboto Mono', monospace;">${changeSign}${changeStr}%</span>
            </div>
          `
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '12%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: data.dates,
        axisLine: { 
          lineStyle: { 
            color: isDark ? '#334155' : '#e2e8f0',
            width: 1
          } 
        },
        axisLabel: { 
          color: isDark ? '#94a3b8' : '#64748b',
          fontSize: 11,
          fontFamily: 'Roboto Mono, monospace'
        },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLine: { show: false },
        splitLine: { 
          lineStyle: { 
            color: isDark ? '#1e293b' : '#f1f5f9',
            type: 'dashed'
          } 
        },
        axisLabel: { 
          color: isDark ? '#94a3b8' : '#64748b',
          fontSize: 11,
          fontFamily: 'Roboto Mono, monospace',
          formatter: (value: number) => value?.toFixed(3) || '--'
        }
      },
      series: [{
        name: '单位净值',
        type: 'line',
        smooth: false,  // 使用直线而非平滑线
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: false,  // 默认不显示点，hover时显示
        lineStyle: {
          width: 2,
          color: colors.primary
        },
        itemStyle: {
          color: colors.primary,
          borderWidth: 2,
          borderColor: isDark ? '#0f172a' : '#ffffff'
        },
        emphasis: {
          scale: 1.5,
          itemStyle: {
            borderWidth: 3
          }
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: colors.gradientStart },
            { offset: 1, color: colors.gradientEnd }
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
