<template>
  <el-dialog
    v-model="visible"
    :title="$t('fund.detailTitle')"
    width="1000px"
    destroy-on-close
    align-center
    class="fund-detail-dialog"
  >
    <!-- 头部信息 -->
    <div class="fund-header">
      <div class="fund-basic">
        <h2 class="fund-name">{{ fundData?.name }}</h2>
        <span class="fund-code">{{ fundData?.code }}</span>
        <el-tag :type="getStatusType(fundData?.status)" size="small" effect="light">
          {{ fundData?.status }}
        </el-tag>
      </div>
      <div class="fund-nav">
        <div class="nav-value" :class="getChangeClass(fundData?.estimate_change)">
          {{ formatNav(fundData?.estimate_nav) }}
        </div>
        <div class="nav-change" :class="getChangeClass(fundData?.estimate_change)">
          <el-icon v-if="(fundData?.estimate_change ?? 0) > 0" size="14"><ArrowUp /></el-icon>
          <el-icon v-else-if="(fundData?.estimate_change ?? 0) < 0" size="14"><ArrowDown /></el-icon>
          <span>{{ formatChange(fundData?.estimate_change) }}</span>
        </div>
      </div>
    </div>

    <el-divider />

    <!-- 统计信息 - 增长率指标 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <div class="stat-item">
          <div class="stat-label">日增长率</div>
          <div class="stat-value" :class="getChangeClass(growthRates.daily)">
            {{ formatChange(growthRates.daily) }}
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-item">
          <div class="stat-label">3月增长率</div>
          <div class="stat-value" :class="getChangeClass(growthRates.threeMonth)">
            {{ formatChange(growthRates.threeMonth) }}
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-item">
          <div class="stat-label">半年增长率</div>
          <div class="stat-value" :class="getChangeClass(growthRates.sixMonth)">
            {{ formatChange(growthRates.sixMonth) }}
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-item">
          <div class="stat-label">年增长率</div>
          <div class="stat-value" :class="getChangeClass(growthRates.oneYear)">
            {{ formatChange(growthRates.oneYear) }}
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表区域 - 使用 FundChart 组件 -->
    <div class="chart-section">
      <FundChart v-if="fundData" :code="fundData.code" :name="fundData.name" />
    </div>

    <!-- 操作按钮 -->
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">{{ $t('common.close') }}</el-button>
        <el-button type="primary" :icon="Plus" @click="addToPortfolio">
          {{ $t('portfolio.addPosition') }}
        </el-button>
        <el-button type="success" :icon="Star" @click="addToWatchlist">
          {{ $t('fund.addToWatchlist') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { ArrowUp, ArrowDown, Loading, Plus, Star } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/fundStore'
import { usePortfolioStore } from '@/stores/portfolioStore'
import FundChart from '@/components/Charts/FundChart.vue'
import fundApi from '@/api/fund'
import type { FundRealtimeData } from '@/api/fund'

const { t } = useI18n()
const fundStore = useFundStore()
const portfolioStore = usePortfolioStore()

const props = defineProps<{
  modelValue: boolean
  fund: FundRealtimeData | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

// 状态
const visible = ref(props.modelValue)
const fundData = ref<FundRealtimeData | null>(props.fund)

// 增长率数据
const growthRates = ref({
  daily: null as number | null,
  threeMonth: null as number | null,
  sixMonth: null as number | null,
  oneYear: null as number | null
})

// 监听visible变化
watch(() => props.modelValue, async (val) => {
  visible.value = val
  if (val && props.fund) {
    fundData.value = { ...props.fund }
    // 重新获取最新数据
    await refreshFundData()
    // 加载增长率数据
    await loadGrowthRates()
  }
})

watch(() => visible.value, (val) => {
  emit('update:modelValue', val)
})

watch(() => props.fund, (val) => {
  fundData.value = val
})

// 格式化净值
const formatNav = (val: string | number | null | undefined) => {
  if (val === null || val === undefined || val === '') return '--'
  const num = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(num)) return '--'
  return num.toFixed(4)
}

// 刷新基金数据
const refreshFundData = async () => {
  if (!fundData.value?.code) return
  try {
    const freshData = await fundApi.getRealtime(fundData.value.code)
    if (freshData) {
      fundData.value = { ...fundData.value, ...freshData }
    }
  } catch (e) {
    console.warn('获取最新基金数据失败:', e)
    // 使用传入的数据，不阻断流程
  }
}

// 加载各时间段增长率
const loadGrowthRates = async () => {
  if (!fundData.value?.code) return

  try {
    // 日增长率使用实时数据
    growthRates.value.daily = fundData.value?.estimate_change ?? null

    // 并行获取各时间段的历史数据
    const [threeMonthRes, sixMonthRes, oneYearRes] = await Promise.all([
      fundApi.getHistory(fundData.value.code, '3M').catch(() => null),
      fundApi.getHistory(fundData.value.code, '6M').catch(() => null),
      fundApi.getHistory(fundData.value.code, '1Y').catch(() => null)
    ])

    const threeMonthData = threeMonthRes?.data
    const sixMonthData = sixMonthRes?.data
    const oneYearData = oneYearRes?.data

    // 计算3月增长率
    if (threeMonthData && threeMonthData.values.length >= 2) {
      const start = Number(threeMonthData.values[0])
      const end = Number(threeMonthData.values[threeMonthData.values.length - 1])
      if (start > 0) {
        growthRates.value.threeMonth = ((end - start) / start) * 100
      }
    }

    // 计算半年增长率
    if (sixMonthData && sixMonthData.values.length >= 2) {
      const start = Number(sixMonthData.values[0])
      const end = Number(sixMonthData.values[sixMonthData.values.length - 1])
      if (start > 0) {
        growthRates.value.sixMonth = ((end - start) / start) * 100
      }
    }

    // 计算年增长率
    if (oneYearData && oneYearData.values.length >= 2) {
      const start = Number(oneYearData.values[0])
      const end = Number(oneYearData.values[oneYearData.values.length - 1])
      if (start > 0) {
        growthRates.value.oneYear = ((end - start) / start) * 100
      }
    }
  } catch (e) {
    console.warn('加载增长率数据失败:', e)
  }
}

// 格式化涨跌幅
const formatChange = (val: number | string | null | undefined) => {
  if (val === null || val === undefined) return '--'
  const num = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(num)) return '--'
  return (num > 0 ? '+' : '') + num.toFixed(2) + '%'
}

// 获取涨跌样式
const getChangeClass = (val: number | null | undefined) => {
  if (val === null || val === undefined) return ''
  if (val > 0) return 'text-success'
  if (val < 0) return 'text-danger'
  return ''
}

// 获取状态标签类型
const getStatusType = (status: string | undefined): 'success' | 'info' | 'warning' | 'danger' => {
  if (!status) return 'info'
  if (status === '正常') return 'success'
  if (status === '最新净值') return 'info'
  if (status === '场内行情') return 'warning'
  return 'info'
}

// 添加到持仓
const addToPortfolio = async () => {
  if (!fundData.value) return

  try {
    const nav = typeof fundData.value.estimate_nav === 'string'
      ? parseFloat(fundData.value.estimate_nav)
      : fundData.value.estimate_nav
    const shares = 100
    const costAmount = (nav || 1.0) * shares

    const success = await portfolioStore.addItem({
      fund_code: fundData.value.code,
      fund_name: fundData.value.name,
      hold_shares: shares,
      cost_amount: costAmount,
      cost_nav: nav || undefined
    })

    if (success) {
      ElMessage.success(t('portfolio.addSuccess', { name: fundData.value.name }))
    } else {
      ElMessage.error(t('portfolio.addFailed'))
    }
  } catch {
    ElMessage.error(t('portfolio.addFailed'))
  }
}

// 添加到关注列表
const addToWatchlist = async () => {
  if (!fundData.value) return

  try {
    const exists = fundStore.fundList.includes(fundData.value.code)
    if (exists) {
      ElMessage.warning(t('fund.alreadyInWatchlist'))
      return
    }

    fundStore.fundList.push(fundData.value.code)
    await fundStore.fetchRealtimeData()
    ElMessage.success(t('fund.addSuccess', { name: fundData.value.name }))
  } catch {
    ElMessage.error(t('fund.addFailed'))
  }
}
</script>

<style scoped lang="scss">
.fund-detail-dialog {
  :deep(.el-dialog__body) {
    padding: 20px;
  }

  .fund-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    .fund-basic {
      display: flex;
      align-items: center;
      gap: 12px;

      .fund-name {
        margin: 0;
        font-size: 20px;
        font-weight: 600;
        color: var(--text-primary);
      }

      .fund-code {
        font-size: 14px;
        color: var(--text-secondary);
        font-family: monospace;
      }
    }

    .fund-nav {
      text-align: right;

      .nav-value {
        font-size: 28px;
        font-weight: 700;
        line-height: 1.2;
      }

      .nav-change {
        font-size: 14px;
        margin-top: 4px;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 4px;
      }
    }
  }

  .stats-row {
    margin-bottom: 24px;

    .stat-item {
      text-align: center;
      padding: 12px;
      background: var(--bg-page);
      border-radius: var(--radius-base);

      .stat-label {
        font-size: 12px;
        color: var(--text-secondary);
        margin-bottom: 4px;
      }

      .stat-value {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
      }
    }
  }

  .chart-section {
    margin-top: 20px;
  }

  .text-success {
    color: var(--success-color);
  }

  .text-danger {
    color: var(--danger-color);
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
}
</style>
