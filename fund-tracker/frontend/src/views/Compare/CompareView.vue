<template>
  <div class="compare-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">{{ $t('compare.title') }}</span>
          <el-icon v-if="loading" class="is-loading" size="16"><Loading /></el-icon>
        </div>
      </template>

      <el-form :model="form" inline class="compare-form">
        <el-form-item :label="$t('compare.selectFunds')">
          <el-select
            v-model="form.codes"
            multiple
            filterable
            :placeholder="$t('compare.selectPlaceholder')"
            style="width: 320px"
            :max-collapse-tags="2"
          >
            <el-option
              v-for="fund in fundStore.realtimeData"
              :key="fund.code"
              :label="`${fund.name} (${fund.code})`"
              :value="fund.code"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('compare.timeRange')">
          <el-radio-group v-model="form.range" size="small">
            <el-radio-button value="1W">1{{ $t('common.week') }}</el-radio-button>
            <el-radio-button value="1M">1{{ $t('common.month') }}</el-radio-button>
            <el-radio-button value="3M">3{{ $t('common.month') }}</el-radio-button>
            <el-radio-button value="6M">6{{ $t('common.month') }}</el-radio-button>
            <el-radio-button value="1Y">1{{ $t('common.year') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="form.includeBenchmark" :label="$t('compare.showBenchmark')" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleCompare" :loading="loading" size="small">
            {{ $t('compare.startCompare') }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider v-if="compareData.length > 0" />

      <!-- 空状态 -->
      <el-empty v-if="compareData.length === 0 && !loading" :description="$t('compare.emptyTip')">
        <template #description>
          <p>{{ $t('compare.emptyTip') }}</p>
        </template>
      </el-empty>

      <!-- 对比结果 -->
      <div v-else-if="compareData.length > 0" class="compare-result">
        <div ref="chartRef" class="chart-container"></div>

        <!-- 多周期涨跌幅对比表格 -->
        <div class="multi-period-section">
          <h4 class="section-title">
            <el-icon><TrendCharts /></el-icon>
            多周期涨跌幅对比
          </h4>
          <el-table 
            :data="compareDataWithReturns" 
            stripe 
            class="compare-table" 
            size="small"
            border
          >
            <el-table-column prop="name" :label="$t('home.fundList.name')" min-width="180" show-overflow-tooltip fixed="left" />
            <el-table-column prop="code" :label="$t('home.fundList.code')" width="100" fixed="left" />
            
            <!-- 短期 -->
            <el-table-column label="短期" align="center">
              <el-table-column prop="returns.d3" label="3日" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.d3)">
                    {{ formatChange(row.returns?.d3) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="returns.d7" label="7日" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.d7)">
                    {{ formatChange(row.returns?.d7) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="returns.d30" label="30日" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.d30)">
                    {{ formatChange(row.returns?.d30) }}
                  </span>
                </template>
              </el-table-column>
            </el-table-column>
            
            <!-- 中期 -->
            <el-table-column label="中期" align="center">
              <el-table-column prop="returns.m3" label="3月" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.m3)">
                    {{ formatChange(row.returns?.m3) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="returns.m6" label="6月" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.m6)">
                    {{ formatChange(row.returns?.m6) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="returns.y1" label="1年" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.y1)">
                    {{ formatChange(row.returns?.y1) }}
                  </span>
                </template>
              </el-table-column>
            </el-table-column>
            
            <!-- 长期 -->
            <el-table-column label="长期" align="center">
              <el-table-column prop="returns.y3" label="3年" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.y3)">
                    {{ formatChange(row.returns?.y3) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="returns.y5" label="5年" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.y5)">
                    {{ formatChange(row.returns?.y5) }}
                  </span>
                </template>
              </el-table-column>
            </el-table-column>
            
            <!-- 当前涨跌幅 -->
            <el-table-column prop="currentChange" label="当前涨跌" width="100" align="right" fixed="right">
              <template #default="{ row }">
                <span :class="getChangeClass(row.currentChange)">
                  {{ formatChange(row.currentChange) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 基准指数显示 -->
        <div v-if="benchmarkData.length > 0" class="benchmark-section">
          <h4 class="section-title">
            <el-icon><TrendCharts /></el-icon>
            {{ $t('compare.benchmarkIndex') }}
          </h4>
          <el-table :data="benchmarkDataWithReturns" stripe size="small" border>
            <el-table-column prop="name" :label="$t('compare.benchmarkName')" min-width="180" show-overflow-tooltip fixed="left" />
            
            <!-- 短期 -->
            <el-table-column label="短期" align="center">
              <el-table-column prop="returns.d3" label="3日" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.d3)">
                    {{ formatChange(row.returns?.d3) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="returns.d7" label="7日" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.d7)">
                    {{ formatChange(row.returns?.d7) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="returns.d30" label="30日" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.d30)">
                    {{ formatChange(row.returns?.d30) }}
                  </span>
                </template>
              </el-table-column>
            </el-table-column>
            
            <!-- 中期 -->
            <el-table-column label="中期" align="center">
              <el-table-column prop="returns.m3" label="3月" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.m3)">
                    {{ formatChange(row.returns?.m3) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="returns.m6" label="6月" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.m6)">
                    {{ formatChange(row.returns?.m6) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="returns.y1" label="1年" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.y1)">
                    {{ formatChange(row.returns?.y1) }}
                  </span>
                </template>
              </el-table-column>
            </el-table-column>
            
            <!-- 长期 -->
            <el-table-column label="长期" align="center">
              <el-table-column prop="returns.y3" label="3年" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.y3)">
                    {{ formatChange(row.returns?.y3) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="returns.y5" label="5年" width="90" align="right">
                <template #default="{ row }">
                  <span :class="getChangeClass(row.returns?.y5)">
                    {{ formatChange(row.returns?.y5) }}
                  </span>
                </template>
              </el-table-column>
            </el-table-column>
            
            <!-- 当前涨跌幅 -->
            <el-table-column prop="currentChange" label="当前涨跌" width="100" align="right" fixed="right">
              <template #default="{ row }">
                <span :class="getChangeClass(row.currentChange)">
                  {{ formatChange(row.currentChange) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'CompareView'
})

import { reactive, ref, onMounted, nextTick, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import { Loading, TrendCharts } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { useFundStore } from '@/stores/fundStore'
import fundApi from '@/api/fund'
import { ElMessage } from 'element-plus'

const { t } = useI18n()
const fundStore = useFundStore()

const form = reactive({
  codes: [] as string[],
  range: '1M',
  includeBenchmark: true
})

interface FundCompareData {
  code: string
  name: string
  dates: string[]
  changes: number[]
  currentChange?: number
  returns?: {
    d3?: number
    d7?: number
    d30?: number
    m3?: number
    m6?: number
    y1?: number
    y3?: number
    y5?: number
  }
}

const compareData = ref<FundCompareData[]>([])

interface BenchmarkData {
  name: string
  symbol: string
  dates: string[]
  changes: number[]
  currentChange?: number
  returns?: {
    d3?: number
    d7?: number
    d30?: number
    m3?: number
    m6?: number
    y1?: number
    y3?: number
    y5?: number
  }
}

const benchmarkData = ref<BenchmarkData[]>([])
const chartRef = ref<HTMLElement>()
const loading = ref(false)
let chart: echarts.ECharts | null = null

// 带多周期数据的基准指数数据
const benchmarkDataWithReturns = computed(() => {
  return benchmarkData.value.map(bench => ({
    ...bench,
    returns: calculateReturns(bench.changes),
    currentChange: bench.changes && bench.changes.length > 0 
      ? bench.changes[bench.changes.length - 1] 
      : undefined
  }))
})

// 金融专业配色方案
const financialColors = {
  primary: ['#1e3a8a', '#0f766e', '#b45309', '#7c3aed', '#be123c'],
  secondary: ['#3b82f6', '#14b8a6', '#f59e0b', '#8b5cf6', '#f43f5e'],
  benchmark: ['#64748b', '#94a3b8']
}

const formatChange = (val: number | string | null | undefined) => {
  if (val === null || val === undefined) return '--'
  const num = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(num)) return '--'
  return (num > 0 ? '+' : '') + num.toFixed(2) + '%'
}

const getChangeClass = (val: number | string | null | undefined) => {
  if (val === null || val === undefined) return ''
  const num = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(num)) return ''
  if (num > 0) return 'text-success'
  if (num < 0) return 'text-danger'
  return ''
}

// 计算多周期涨跌幅
const calculateReturns = (changes: number[]): FundCompareData['returns'] => {
  if (!changes || changes.length === 0) return {}
  
  // 计算累计收益率
  const calculateCumulative = (days: number): number | undefined => {
    if (changes.length < days) {
      // 数据不足，无法计算该周期
      return undefined
    }
    if (days === 0) return undefined
    
    const recentChanges = changes.slice(-days)
    // 累计收益率 = (1+r1)*(1+r2)*...*(1+rn) - 1
    let cumulative = 1
    for (const change of recentChanges) {
      cumulative *= (1 + change / 100)
    }
    return (cumulative - 1) * 100
  }
  
  return {
    d3: calculateCumulative(3),
    d7: calculateCumulative(7),
    d30: calculateCumulative(30),
    m3: calculateCumulative(90),
    m6: calculateCumulative(180),
    y1: calculateCumulative(365),
    y3: calculateCumulative(1095),
    y5: calculateCumulative(1825)
  }
}

// 带多周期数据的对比数据
const compareDataWithReturns = computed(() => {
  return compareData.value.map(fund => ({
    ...fund,
    returns: calculateReturns(fund.changes),
    currentChange: fund.changes && fund.changes.length > 0 
      ? fund.changes[fund.changes.length - 1] 
      : undefined
  }))
})

const handleCompare = async () => {
  if (form.codes.length < 2) {
    ElMessage.warning(t('compare.selectAtLeastTwo'))
    return
  }

  loading.value = true
  try {
    const result = await fundApi.compare(form.codes, form.range, form.includeBenchmark)
    
    // 处理基金数据
    compareData.value = (result.funds || []).map(fund => ({
      ...fund,
      currentChange: fund.changes && fund.changes.length > 0 
        ? fund.changes[fund.changes.length - 1] 
        : undefined
    }))
    
    // 处理基准数据
    benchmarkData.value = (result.benchmarks || []).map(bench => ({
      ...bench,
      change: bench.changes && bench.changes.length > 0 
        ? bench.changes[bench.changes.length - 1] 
        : undefined
    }))

    await nextTick()

    if (compareData.value.length > 0) {
      initChart()
      updateChart(compareData.value, benchmarkData.value)
    }
  } catch (e) {
    console.error('对比失败:', e)
    ElMessage.error(t('common.error'))
  } finally {
    loading.value = false
  }
}

const initChart = () => {
  if (!chartRef.value) return

  if (chart) {
    chart.dispose()
  }

  chart = echarts.init(chartRef.value)

  const handleResize = () => chart?.resize()
  window.addEventListener('resize', handleResize)
}

const updateChart = (
  funds: Array<{ name: string; dates?: string[]; changes?: number[] }>,
  benchmarks: Array<{ name: string; dates?: string[]; changes?: number[] }> = []
) => {
  if (!chart || funds.length === 0) return

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  const colors = isDark ? financialColors.secondary : financialColors.primary
  const benchColors = isDark ? ['#94a3b8', '#cbd5e1'] : financialColors.benchmark

  const allSeries: echarts.SeriesOption[] = []

  funds.forEach((fund, index) => {
    allSeries.push({
      name: fund.name,
      type: 'line' as const,
      smooth: false,  // 使用直线
      symbol: 'circle',
      symbolSize: 4,
      showSymbol: false,
      data: fund.changes || [],
      lineStyle: { 
        width: 2,
        color: colors[index % colors.length]
      },
      itemStyle: { 
        color: colors[index % colors.length],
        borderWidth: 2,
        borderColor: isDark ? '#0f172a' : '#ffffff'
      },
      emphasis: { 
        lineStyle: { width: 3 },
        scale: 1.5
      }
    })
  })

  benchmarks.forEach((bench, index) => {
    allSeries.push({
      name: `[${bench.name}]`,
      type: 'line' as const,
      smooth: false,
      symbol: 'none' as const,
      data: bench.changes || [],
      lineStyle: { 
        width: 2, 
        type: 'dashed',
        color: benchColors[index % benchColors.length]
      },
      itemStyle: { 
        color: benchColors[index % benchColors.length]
      }
    })
  })

  const allNames = [
    ...funds.map(f => f.name),
    ...benchmarks.map(b => `[${b.name}]`)
  ]

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
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
        if (!params.length) return ''
        let result = `<div style="font-weight:600;margin-bottom:8px;color:${isDark ? '#f8fafc' : '#1e293b'}">${params[0].axisValue}</div>`
        params.forEach((p: any) => {
          const value = p.value !== null && p.value !== undefined ? `${p.value.toFixed(2)}%` : '--'
          const color = p.value > 0 ? '#dc2626' : p.value < 0 ? '#16a34a' : '#64748b'
          result += `<div style="display:flex;justify-content:space-between;gap:16px;margin:4px 0">
            <span style="display:flex;align-items:center;gap:8px">
              <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color}"></span>
              <span style="color:${isDark ? '#cbd5e1' : '#475569'}">${p.seriesName}</span>
            </span>
            <span style="color:${color};font-weight:600;font-family:'Roboto Mono',monospace">${value}</span>
          </div>`
        })
        return result
      }
    },
    legend: {
      data: allNames,
      bottom: 0,
      icon: 'roundRect',
      textStyle: { 
        color: isDark ? '#cbd5e1' : '#374151',
        fontSize: 12
      },
      itemWidth: 12,
      itemHeight: 12
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: funds[0]?.dates || [],
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
        formatter: (value: number) => `${value.toFixed(1)}%`
      }
    },
    series: allSeries
  }

  chart.setOption(option, true)
}

onMounted(() => {
})

onUnmounted(() => {
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped lang="scss">
.compare-view {
  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;

    .title {
      font-size: 16px;
      font-weight: 600;
    }
  }

  .compare-form {
    :deep(.el-form-item) {
      margin-bottom: 0;
    }
  }

  .compare-result {
    .chart-container {
      height: 350px;
      margin-bottom: 24px;
      background: var(--bg-base);
      border-radius: 8px;
    }

    .multi-period-section {
      margin-bottom: 24px;

      .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 16px;

        .el-icon {
          color: var(--primary-color);
        }
      }
    }

    .compare-table {
      :deep(.el-table__header) {
        th {
          background: var(--bg-page);
          font-weight: 600;
        }
      }

      :deep(.el-table__cell) {
        padding: 8px 0;
      }
    }
  }

  .benchmark-section {
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px dashed var(--border-base);

    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 15px;
      font-weight: 600;
      color: var(--text-secondary);
      margin-bottom: 12px;

      .el-icon {
        color: var(--primary-color);
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
}
</style>
