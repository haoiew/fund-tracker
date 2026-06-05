<template>
  <div class="result-table">
    <el-table 
      :data="data" 
      v-loading="loading" 
      stripe 
      @expand-change="handleExpandChange"
      :expand-row-keys="expandedRows"
      row-key="code"
    >
      <el-table-column type="expand" width="40">
        <template #default="{ row }">
          <div class="fund-detail-panel">
            <div class="detail-content">
              <!-- 左侧：数据表格 -->
              <div class="detail-left">
                <div class="detail-header">
                  <h4>{{ row.name }} - 近7日净值走势</h4>
                  <el-button 
                    link 
                    type="primary" 
                    size="small"
                    :loading="loadingHistoryMap[row.code]"
                    @click.stop="loadMoreHistory(row)"
                  >
                    加载更多历史数据
                  </el-button>
                </div>
                <div class="history-table-scroll">
                  <div v-if="getHistoryRows(row.code).length > 0" class="history-table-wrapper">
                    <el-table :data="getHistoryRows(row.code)" size="small" border>
                      <el-table-column prop="date" label="日期" width="120" />
                      <el-table-column prop="nav" label="净值" width="95">
                        <template #default="{ row: historyRow }">
                          {{ historyRow.nav !== undefined && historyRow.nav !== null ? historyRow.nav.toFixed(4) : '--' }}
                        </template>
                      </el-table-column>
                      <el-table-column prop="change_pct" label="涨跌幅" width="85">
                        <template #default="{ row: historyRow }">
                          <span :class="getChangeClass(historyRow.change_pct)">
                            {{ formatChange(historyRow.change_pct) }}
                          </span>
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
                  <div v-else-if="loadingHistoryMap[row.code]" class="loading-text">
                    <el-icon class="is-loading"><Loading /></el-icon>
                    <span>加载中...</span>
                  </div>
                  <div v-else class="empty-text">
                    暂无历史数据
                  </div>
                </div>
              </div>
              
              <!-- 右侧：图表 -->
              <div class="detail-right">
                <div ref="chartRef" class="mini-chart" :id="`chart-${row.code}`"></div>
              </div>
            </div>
          </div>
        </template>
      </el-table-column>
      
      <el-table-column prop="code" label="基金代码" width="120" />
      <el-table-column prop="name" label="基金名称" min-width="200" show-overflow-tooltip />
      <el-table-column prop="days" :label="screenType === 'period' ? '统计天数' : '连续天数'" width="100" sortable>
        <template #default="{ row }">
          <el-tag :type="direction === 'up' ? 'danger' : 'success'" size="small" effect="dark">
            {{ row.days }}天
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="pct" label="累计涨跌幅" width="150" sortable>
        <template #default="{ row }">
          <span :class="row.pct >= 0 ? 'text-success' : 'text-danger'">
            {{ row.pct >= 0 ? '+' : '' }}{{ row.pct.toFixed(2) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="$emit('view', row)">
            图表
          </el-button>
          <el-button link type="success" size="small" @click.stop="$emit('add', row)">
            关注
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!loading && data.length === 0" description="暂无数据" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { fundApi, type FundTrendResult, type ScreenType } from '@/api/fund'

interface Props {
  data: FundTrendResult[]
  loading: boolean
  direction: 'up' | 'down'
  screenType?: ScreenType
}

const props = defineProps<Props>()

const emit = defineEmits<{
  view: [fund: FundTrendResult]
  add: [fund: FundTrendResult]
}>()

// 展开的行
const expandedRows = ref<string[]>([])

// 历史数据 - 每个基金独立存储
const historyData = reactive<Record<string, any[]>>({})
const getHistoryRows = (code: string) => historyData[code] ?? []

// 每个基金的加载状态
const loadingHistoryMap = reactive<Record<string, boolean>>({})

// 图表实例
const chartInstances = reactive<Record<string, echarts.ECharts | null>>({})

// 处理展开/收起
const handleExpandChange = async (row: FundTrendResult, expandedRowsList: any[]) => {
  const isExpanded = expandedRowsList.includes(row)
  
  if (isExpanded) {
    // 展开 - 添加到展开列表
    if (!expandedRows.value.includes(row.code)) {
      expandedRows.value.push(row.code)
    }
    
    // 如果还没有加载历史数据，自动加载近7日
    if (!historyData[row.code]?.length) {
      await loadHistoryData(row.code, 7)
    }
    
    // 渲染图表
    await nextTick()
    renderChart(row.code)
  } else {
    // 收起 - 从展开列表移除
    const index = expandedRows.value.indexOf(row.code)
    if (index > -1) {
      expandedRows.value.splice(index, 1)
    }
    
    // 销毁图表实例
    if (chartInstances[row.code]) {
      chartInstances[row.code]?.dispose()
      chartInstances[row.code] = null
    }
  }
}

// 渲染迷你图表
const renderChart = (code: string) => {
  const chartDom = document.getElementById(`chart-${code}`)
  if (!chartDom) return
  
  // 销毁旧实例
  if (chartInstances[code]) {
    chartInstances[code]?.dispose()
  }
  
  const chart = echarts.init(chartDom)
  chartInstances[code] = chart
  
  const data = historyData[code]
  if (!data || data.length === 0) return
  
  // 倒序排列（时间正序）用于图表
  const chartData = [...data].reverse()
  const dates = chartData.map(item => item.date)
  const values = chartData.map(item => item.nav)
  
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  const lineColor = props.direction === 'up' ? '#ef4444' : '#10b981'
  
  const option: echarts.EChartsOption = {
    grid: {
      left: '10%',
      right: '5%',
      top: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { 
        show: true,
        fontSize: 10,
        color: isDark ? '#94a3b8' : '#64748b',
        interval: Math.floor(dates.length / 3)
      }
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { 
        lineStyle: { 
          color: isDark ? '#1e293b' : '#f1f5f9',
          type: 'dashed'
        } 
      },
      axisLabel: { 
        show: true,
        fontSize: 10,
        color: isDark ? '#94a3b8' : '#64748b',
        formatter: (value: number) => value?.toFixed(2) || ''
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = params[0]
        const dataIndex = p.dataIndex
        const item = chartData[dataIndex]
        return `${item.date}<br/>净值: ${item.nav?.toFixed(4)}`
      }
    },
    series: [{
      type: 'line',
      smooth: false,
      symbol: 'none',
      data: values,
      lineStyle: {
        width: 2,
        color: lineColor
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: props.direction === 'up' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)' },
          { offset: 1, color: props.direction === 'up' ? 'rgba(239, 68, 68, 0.05)' : 'rgba(16, 185, 129, 0.05)' }
        ])
      }
    }]
  }
  
  chart.setOption(option)
}

// 加载历史数据
const loadHistoryData = async (code: string, days: number = 7) => {
  // 设置该基金的加载状态
  loadingHistoryMap[code] = true

  try {
    const range = days <= 7 ? '1W' : days <= 30 ? '1M' : '3M'
    const result = await fundApi.getHistory(code, range)
    console.log(`[ResultTable] 基金 ${code} 历史数据API返回:`, result)
    
    // 处理API返回的数据结构: { data: { dates, values, changes }, source, updating }
    const chartData = result?.data || result
    
    if (chartData && Array.isArray(chartData.dates) && Array.isArray(chartData.values)) {
      const dates = chartData.dates
      const values = chartData.values
      const changes = chartData.changes || []
      
      console.log(`[ResultTable] 基金 ${code} 历史数据:`, { 
        dates: dates.length, 
        values: values.length,
        sampleDate: dates[dates.length - 1],
        sampleValue: values[values.length - 1]
      })
      
      // 取最近N天的数据
      const recentData = []
      const count = Math.min(days, dates.length)
      
      for (let i = dates.length - count; i < dates.length; i++) {
        if (i >= 0) {
          const currentNav = Number(values[i])
          const prevNav = i > 0 ? Number(values[i - 1]) : currentNav
          const change = currentNav - prevNav
          const changePct = prevNav > 0 ? (change / prevNav) * 100 : 0
          
          recentData.push({
            date: dates[i],
            nav: currentNav,
            change: change,
            change_pct: changes[i] !== undefined ? Number(changes[i]) : changePct
          })
        }
      }
      
      // 倒序排列（最新的在前）
      historyData[code] = recentData.reverse()
      console.log(`[ResultTable] 基金 ${code} 处理后的历史数据:`, historyData[code])
    } else {
      console.warn(`[ResultTable] 基金 ${code} 没有历史数据`, chartData)
      historyData[code] = []
    }
  } catch (error) {
    console.error(`[ResultTable] 加载基金 ${code} 历史数据失败:`, error)
    ElMessage.error('加载历史数据失败')
    historyData[code] = []
  } finally {
    loadingHistoryMap[code] = false
  }
}

// 加载更多历史数据
const loadMoreHistory = async (row: FundTrendResult) => {
  const currentCount = historyData[row.code]?.length || 0
  const newCount = currentCount + 7
  await loadHistoryData(row.code, newCount)
  
  // 重新渲染图表
  await nextTick()
  renderChart(row.code)
  
  ElMessage.success(`已加载 ${newCount} 天历史数据`)
}

// 获取涨跌样式
const getChangeClass = (value: number | null | undefined) => {
  if (value === null || value === undefined) return ''
  return value >= 0 ? 'text-success' : 'text-danger'
}

// 格式化涨跌幅（带%）
const formatChange = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '--'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}
</script>

<style scoped lang="scss">
.result-table {
  .fund-detail-panel {
    padding: 16px;
    background: var(--bg-page);
    border-radius: var(--radius-base);
    margin: 8px 16px;

    .detail-content {
      display: flex;
      gap: 20px;
      
      .detail-left {
        flex: 0 0 416px; // 320px * 1.3 = 416px
        display: flex;
        flex-direction: column;
        
        .detail-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
          flex-shrink: 0;

          h4 {
            margin: 0;
            font-size: 14px;
            color: var(--text-primary);
          }
        }

        .history-table-scroll {
          flex: 1;
          max-height: 280px; // 刚好显示7行数据的高度
          overflow-y: auto;
          
          .history-table-wrapper {
            :deep(.el-table) {
              .el-table__cell {
                padding: 4px 0;
              }
            }
          }

          .loading-text,
          .empty-text {
            text-align: center;
            padding: 20px;
            color: var(--text-secondary);
            font-size: 13px;
          }
          
          .loading-text {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
          }
        }
      }
      
      .detail-right {
        flex: 1;
        min-width: 300px;
        display: flex;
        align-items: center; // 垂直居中
        justify-content: center; // 水平居中
        
        .mini-chart {
          width: 100%;
          height: 220px; // 固定高度
        }
      }
    }
  }

  .text-success {
    color: var(--success-color);
    font-weight: 600;
  }

  .text-danger {
    color: var(--danger-color);
    font-weight: 600;
  }

  :deep(.el-table__expanded-cell) {
    padding: 0;
  }
  
  :deep(.el-table__expand-icon) {
    cursor: pointer;
  }
}
</style>
