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

        <el-table :data="compareData" stripe class="compare-table" size="small">
          <el-table-column prop="name" :label="$t('home.fundList.name')" min-width="180" show-overflow-tooltip />
          <el-table-column prop="code" :label="$t('home.fundList.code')" width="100" />
          <el-table-column prop="change" :label="$t('compare.currentChange')" width="120" align="right">
            <template #default="{ row }">
              <span :class="getChangeClass(row.change)">
                {{ formatChange(row.change) }}
              </span>
            </template>
          </el-table-column>
        </el-table>

        <!-- 基准指数显示 -->
        <div v-if="benchmarkData.length > 0" class="benchmark-section">
          <h4>{{ $t('compare.benchmarkIndex') }}</h4>
          <el-table :data="benchmarkData" stripe size="small">
            <el-table-column prop="name" :label="$t('compare.benchmarkName')" min-width="150" />
            <el-table-column prop="change" :label="$t('compare.currentChange')" width="150" align="right">
              <template #default="{ row }">
                <span :class="getChangeClass(row.change)">
                  {{ formatChange(row.change) }}
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

import { reactive, ref, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { Loading } from '@element-plus/icons-vue'
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

const compareData = ref<Array<{
  code: string
  name: string
  dates: string[]
  changes: number[]
}>>([])
const benchmarkData = ref<Array<{
  name: string
  symbol: string
  dates: string[]
  changes: number[]
}>>([])
const chartRef = ref<HTMLElement>()
const loading = ref(false)
let chart: echarts.ECharts | null = null

const formatChange = (val: number | string | null) => {
  if (val === null || val === undefined) return '--'
  const num = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(num)) return '--'
  return (num > 0 ? '+' : '') + num.toFixed(2) + '%'
}

const getChangeClass = (val: number | string | null) => {
  if (val === null || val === undefined) return ''
  const num = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(num)) return ''
  if (num > 0) return 'text-success'
  if (num < 0) return 'text-danger'
  return ''
}

const handleCompare = async () => {
  if (form.codes.length < 2) {
    ElMessage.warning(t('compare.selectAtLeastTwo'))
    return
  }

  loading.value = true
  try {
    const result = await fundApi.compare(form.codes, form.range, form.includeBenchmark)
    compareData.value = result.funds || []
    benchmarkData.value = result.benchmarks || []

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

  const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981'] as const
  const benchColors = ['#9ca3af', '#6b7280'] as const

  const allSeries: echarts.SeriesOption[] = []

  funds.forEach((fund, index) => {
    allSeries.push({
      name: fund.name,
      type: 'line' as const,
      smooth: true,
      symbol: 'none' as const,
      data: fund.changes || [],
      lineStyle: { width: 2 },
      itemStyle: { color: colors[index % colors.length] },
      emphasis: { lineStyle: { width: 3 } }
    })
  })

  benchmarks.forEach((bench, index) => {
    allSeries.push({
      name: `[${bench.name}]`,
      type: 'line' as const,
      smooth: true,
      symbol: 'none' as const,
      data: bench.changes || [],
      lineStyle: { width: 2, type: 'dashed' },
      itemStyle: { color: benchColors[index % benchColors.length] }
    })
  })

  const allNames = [
    ...funds.map(f => f.name),
    ...benchmarks.map(b => `[${b.name}]`)
  ]

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: isDark ? '#334155' : '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: isDark ? '#f1f5f9' : '#374151' },
      formatter: (params: any) => {
        if (!params.length) return ''
        let result = `<div style="font-weight:600;margin-bottom:8px">${params[0].axisValue}</div>`
        params.forEach((p: any) => {
          const value = p.value !== null && p.value !== undefined ? `${p.value.toFixed(2)}%` : '--'
          const color = p.value > 0 ? '#ef4444' : p.value < 0 ? '#10b981' : '#6b7280'
          result += `<div style="display:flex;justify-content:space-between;gap:16px;margin:4px 0">
            <span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color};margin-right:8px"></span>${p.seriesName}</span>
            <span style="color:${color};font-weight:600">${value}</span>
          </div>`
        })
        return result
      }
    },
    legend: {
      data: allNames,
      bottom: 0,
      icon: 'roundRect',
      textStyle: { color: isDark ? '#cbd5e1' : '#374151' }
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
      axisLine: { lineStyle: { color: isDark ? '#334155' : '#e5e7eb' } },
      axisLabel: { color: isDark ? '#94a3b8' : '#6b7280' }
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: isDark ? '#334155' : '#f3f4f6' } },
      axisLabel: { color: isDark ? '#94a3b8' : '#6b7280' },
      formatter: (value: number) => `${value.toFixed(0)}%`
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
      margin-bottom: 20px;
      background: var(--bg-base);
      border-radius: 8px;
    }

    .compare-table {
      margin-top: 16px;
    }
  }

  .benchmark-section {
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px dashed var(--border-base);

    h4 {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-secondary);
      margin-bottom: 12px;
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
