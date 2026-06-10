<template>
  <div class="screen-view workbench-page">
    <section class="page-toolbar">
      <div class="page-toolbar__main">
        <span class="page-toolbar__icon">
          <el-icon><Filter /></el-icon>
        </span>
        <div class="page-toolbar__copy">
          <h2 class="page-toolbar__title">条件筛选工作台</h2>
          <p class="page-toolbar__meta">{{ conditions.length }} 组条件 · {{ scopeLabel }} · {{ includeRealtime ? '纳入实时估值' : '仅历史净值' }} · 并行查询</p>
        </div>
      </div>
      <div class="page-toolbar__actions">
        <el-button type="primary" :icon="Plus" @click="addCondition">添加筛选</el-button>
        <el-button :icon="Search" @click="handleScreenAll" :loading="loading">一键查询</el-button>
      </div>
    </section>

    <section class="screen-builder workbench-panel surface-panel">
      <div class="screen-builder-header">
        <div>
          <div class="workbench-panel__title">筛选条件</div>
          <div class="workbench-panel__meta">用统一字段构建连续涨跌或区间累计条件</div>
        </div>
        <div class="screen-builder-actions">
          <div class="screen-mode screen-scope">
            <span class="screen-mode__label">筛选范围</span>
            <el-radio-group v-model="screenScope" class="scope-segment">
              <el-radio-button value="watchlist">关注</el-radio-button>
              <el-radio-button value="portfolio">持仓</el-radio-button>
              <el-radio-button value="market">全市场</el-radio-button>
            </el-radio-group>
          </div>
          <div class="screen-mode">
            <span class="screen-mode__label">实时估值</span>
            <el-tooltip content="开启后将今日实时估值纳入涨跌幅计算；关注和持仓范围会同时纳入可用替代估算" placement="top">
              <el-switch v-model="includeRealtime" active-text="纳入" inactive-text="关闭" />
            </el-tooltip>
          </div>
        </div>
      </div>

      <div class="screen-conditions">
        <div class="condition-rule-list">
          <div
            v-for="condition in conditions"
            :key="condition.id"
            class="condition-rule"
            :class="condition.direction === 'up' ? 'is-up' : 'is-down'"
          >
            <div class="condition-header">
              <div class="condition-title">
                <span class="direction-mark">
                  <el-icon>
                    <component :is="condition.direction === 'up' ? ArrowUp : ArrowDown" />
                  </el-icon>
                </span>
                <div>
                  <span>{{ getConditionLabel(condition) }}</span>
                  <small>{{ condition.type === 'consecutive' ? `${condition.minDays} 天连续` : `${condition.periodDays} 天区间` }} · {{ condition.minPctDisplay }}%</small>
                </div>
              </div>
              <el-button
                v-if="conditions.length > 1"
                circle
                size="small"
                text
                class="condition-remove"
                @click="removeCondition(condition.id)"
              >
                <el-icon><Close /></el-icon>
              </el-button>
            </div>

            <div class="condition-controls">
              <label class="control-field">
                <span class="control-label">类型</span>
                <el-select v-model="condition.type" class="full-width-control">
                  <el-option label="连续涨跌" value="consecutive" />
                  <el-option label="N天内累计" value="period" />
                </el-select>
              </label>

              <label class="control-field">
                <span class="control-label">方向</span>
                <el-radio-group v-model="condition.direction" class="direction-segment">
                  <el-radio-button value="up">上涨</el-radio-button>
                  <el-radio-button value="down">下跌</el-radio-button>
                </el-radio-group>
              </label>

              <label class="control-field" v-if="condition.type === 'consecutive'">
                <span class="control-label">最少天数</span>
                <el-input-number
                  v-model="condition.minDays"
                  :min="1"
                  :max="30"
                  controls-position="right"
                  class="full-width-control"
                />
              </label>

              <label class="control-field" v-else>
                <span class="control-label">统计天数</span>
                <el-input-number
                  v-model="condition.periodDays"
                  :min="1"
                  :max="90"
                  controls-position="right"
                  class="full-width-control"
                />
              </label>

              <label class="control-field">
                <span class="control-label">涨跌幅阈值</span>
                <el-input-number
                  v-model="condition.minPctDisplay"
                  :min="0.1"
                  :max="50"
                  :step="0.5"
                  :precision="1"
                  controls-position="right"
                  class="full-width-control"
                />
              </label>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 筛选结果 -->
    <section v-if="results.length > 0" class="screen-results workbench-panel surface-panel">
      <div class="workbench-panel__header">
        <div>
          <div class="workbench-panel__title">筛选结果</div>
          <div class="workbench-panel__meta">共 {{ results.reduce((sum, item) => sum + item.count, 0) }} 只基金命中</div>
        </div>
      </div>

      <div v-for="result in results" :key="result.conditionId" class="result-section">
        <div class="result-header">
          <div class="result-title">
            <el-icon :class="result.direction === 'up' ? 'up-icon' : 'down-icon'">
              <component :is="result.direction === 'up' ? ArrowUp : ArrowDown" />
            </el-icon>
            <span>{{ getConditionLabelById(result.conditionId) }}</span>
            <el-tag
              :type="result.direction === 'up' ? 'success' : 'danger'"
              size="small"
              effect="dark"
            >
              {{ result.count }}
            </el-tag>
          </div>
        </div>
        <ResultTable
          :data="result.funds"
          :loading="result.loading"
          :direction="result.direction"
          :screen-type="getConditionTypeById(result.conditionId)"
          @view="viewFund"
          @add="addToWatchlist"
        />
      </div>
    </section>

    <!-- 基金图表弹窗 -->
    <el-dialog
      v-model="chartVisible"
      :title="$t('fund.chartTitle')"
      width="900px"
      destroy-on-close
      align-center
    >
      <FundChart v-if="selectedFund" :code="selectedFund.code" :name="selectedFund.name" :default-range="selectedChartRange" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'ScreenView'
})

import { computed, ref } from 'vue'
import { Plus, Close, ArrowUp, ArrowDown, Search } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/fundStore'
import FundChart from '@/components/Charts/FundChart.vue'
import ResultTable from './components/ResultTable.vue'
import { fundApi, type ScreenType, type ScreenUniverse, type FundTrendResult } from '@/api/fund'
import { loadAppSettings } from '@/platform/appSettings'
import { dataManager } from '@/stores/dataManager'

const { t } = useI18n()
const fundStore = useFundStore()

interface ConditionItem {
  id: string
  type: ScreenType
  direction: 'up' | 'down'
  minDays: number
  periodDays: number
  minPctDisplay: number
}

interface ResultItem {
  conditionId: string
  direction: 'up' | 'down'
  count: number
  funds: FundTrendResult[]
  loading: boolean
}

type ScreenScope = 'watchlist' | 'portfolio' | 'market'

interface ScreenTarget {
  codes?: string[]
  universe: ScreenUniverse
  limit?: number
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2, 9)
}

// 默认两个筛选条件
const conditions = ref<ConditionItem[]>([
  {
    id: generateId(),
    type: 'consecutive',
    direction: 'up',
    minDays: 2,
    periodDays: 7,
    minPctDisplay: 3
  },
  {
    id: generateId(),
    type: 'period',
    direction: 'down',
    minDays: 2,
    periodDays: 7,
    minPctDisplay: 5
  }
])

const results = ref<ResultItem[]>([])
const loading = ref(false)
const includeRealtime = ref(true)
const screenScope = ref<ScreenScope>('watchlist')
const chartVisible = ref(false)
const selectedFund = ref<FundTrendResult | null>(null)
const selectedChartRange = ref('1W')

const scopeLabel = computed(() => {
  if (screenScope.value === 'portfolio') return '持仓列表'
  if (screenScope.value === 'market') return '全市场Top10'
  return '关注列表'
})

// 查找基金所属的筛选条件ID
function findConditionIdByFund(fund: FundTrendResult): string | undefined {
  for (const result of results.value) {
    if (result.funds.some(f => f.code === fund.code)) {
      return result.conditionId
    }
  }
  return undefined
}

// 根据筛选条件计算合适的图表时间范围
function calcChartRange(conditionId: string): string {
  const condition = conditions.value.find(c => c.id === conditionId)
  if (!condition) return '1W'
  const days = condition.type === 'consecutive' ? (condition.minDays ?? 2) : (condition.periodDays ?? 7)
  if (days <= 7) return '1W'
  if (days <= 30) return '1M'
  if (days <= 90) return '3M'
  return '6M'
}

function getConditionLabel(condition: ConditionItem): string {
  const typeLabel = condition.type === 'consecutive' ? '连续' : `${condition.periodDays}天内`
  const directionLabel = condition.direction === 'up' ? '上涨' : '下跌'
  return `${typeLabel}${directionLabel}`
}

function getConditionLabelById(conditionId: string): string {
  const condition = conditions.value.find(c => c.id === conditionId)
  return condition ? getConditionLabel(condition) : '未知筛选'
}

function getConditionTypeById(conditionId: string): ScreenType {
  const condition = conditions.value.find(c => c.id === conditionId)
  return condition?.type ?? 'consecutive'
}

function addCondition() {
  conditions.value.push({
    id: generateId(),
    type: 'consecutive',
    direction: 'up',
    minDays: 2,
    periodDays: 7,
    minPctDisplay: 3
  })
}

function removeCondition(id: string) {
  conditions.value = conditions.value.filter(c => c.id !== id)
  results.value = results.value.filter(r => r.conditionId !== id)
}

function getCalendarDaysSetting(): boolean {
  return loadAppSettings().dayCountMode === 'calendar'
}

async function resolveScreenTarget(): Promise<ScreenTarget | null> {
  if (screenScope.value === 'market') {
    return { universe: 'market', limit: 10 }
  }

  if (screenScope.value === 'portfolio') {
    await dataManager.loadPortfolio()
    const codes = [...new Set(dataManager.getState().portfolioItems.map(item => item.fund_code).filter(Boolean))]
    if (codes.length === 0) {
      ElMessage.warning('持仓列表为空，请先添加持仓基金')
      return null
    }
    return { codes, universe: 'local' }
  }

  await fundStore.initFundList()
  const codes = [...new Set(fundStore.fundList)]
  if (codes.length === 0) {
    ElMessage.warning('关注列表为空，请先添加关注基金')
    return null
  }
  return { codes, universe: 'local' }
}

async function handleScreenAll() {
  const target = await resolveScreenTarget()
  if (!target) {
    return
  }

  loading.value = true

  results.value = conditions.value.map(c => ({
    conditionId: c.id,
    direction: c.direction,
    count: 0,
    funds: [],
    loading: true
  }))

  try {
    const calendarDays = getCalendarDaysSetting()
    const promises = conditions.value.map(async (condition) => {
      try {
        const minPct = condition.minPctDisplay / 100
        if (condition.type === 'consecutive') {
          const result = await fundApi.screen(
            condition.direction,
            condition.minDays,
            minPct,
            target.codes,
            includeRealtime.value,
            target.universe,
            target.limit
          )
          return { conditionId: condition.id, direction: condition.direction, count: result.count, funds: result.funds, loading: false }
        } else {
          const result = await fundApi.screenPeriod(
            condition.direction,
            condition.periodDays,
            minPct,
            target.codes,
            includeRealtime.value,
            calendarDays,
            target.universe,
            target.limit
          )
          return { conditionId: condition.id, direction: condition.direction, count: result.count, funds: result.funds, loading: false }
        }
      } catch {
        return { conditionId: condition.id, direction: condition.direction, count: 0, funds: [], loading: false }
      }
    })

    results.value = await Promise.all(promises)
    const totalCount = results.value.reduce((sum, r) => sum + r.count, 0)
    if (totalCount === 0) {
      ElMessage.info('未找到符合条件的基金')
    } else {
      ElMessage.success(`查询完成，${scopeLabel.value}共找到 ${totalCount} 只基金`)
    }
  } catch {
    ElMessage.error('筛选失败')
  } finally {
    loading.value = false
  }
}

function viewFund(fund: FundTrendResult) {
  selectedFund.value = fund
  const conditionId = findConditionIdByFund(fund)
  selectedChartRange.value = conditionId ? calcChartRange(conditionId) : '1W'
  chartVisible.value = true
}

async function addToWatchlist(fund: FundTrendResult) {
  if (fundStore.fundList.includes(fund.code)) {
    ElMessage.warning(t('fund.alreadyInWatchlist'))
    return
  }
  fundStore.addFund(fund.code)
  ElMessage.success(t('fund.addSuccess', { name: fund.name }))
}
</script>

<style scoped lang="scss">
.screen-view {
  .screen-conditions {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .screen-builder-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border-light);
  }

  .screen-builder-actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    flex-wrap: wrap;
    gap: 10px;
    min-width: 0;
  }

  .screen-mode {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background: var(--bg-base);
  }

  .screen-mode__label {
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 700;
  }

  .scope-segment {
    :deep(.el-radio-button__inner) {
      height: 30px;
      min-width: 58px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0 10px;
      border-radius: var(--radius-sm) !important;
      font-size: 12px;
      font-weight: 800;
    }
  }

  .condition-rule-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .condition-rule {
    position: relative;
    display: grid;
    grid-template-columns: minmax(190px, 0.28fr) minmax(0, 1fr);
    align-items: end;
    gap: 14px;
    min-width: 0;
    padding: 12px 14px 12px 16px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background:
      linear-gradient(90deg, rgba(37, 99, 235, 0.026), rgba(37, 99, 235, 0)),
      var(--bg-card);
    box-shadow: var(--shadow-light);
    overflow: hidden;

    &::before {
      content: '';
      position: absolute;
      inset: 0 auto 0 0;
      width: 3px;
      background: var(--primary-color);
    }

    &.is-up::before {
      background: var(--success-color);
    }

    &.is-down::before {
      background: var(--danger-color);
    }
  }

  .condition-header {
    display: flex;
    align-items: center;
    align-self: start;
    justify-content: space-between;
    gap: 10px;
    min-width: 0;
  }

  .condition-title {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    font-size: 14px;
    font-weight: 800;
    color: var(--text-primary);

    small {
      display: block;
      margin-top: 2px;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 600;
    }
  }

  .direction-mark {
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-base);
    background: var(--bg-hover);
    color: var(--primary-color);
  }

  .condition-rule.is-up .direction-mark {
    color: var(--success-color);
    background: var(--success-light);
  }

  .condition-rule.is-down .direction-mark {
    color: var(--danger-color);
    background: var(--danger-light);
  }

  .condition-remove {
    color: var(--text-secondary);
  }

  .condition-controls {
    display: grid;
    grid-template-columns: minmax(140px, 1fr) minmax(148px, 0.9fr) minmax(118px, 0.72fr) minmax(128px, 0.78fr);
    gap: 10px;
    min-width: 0;
    align-items: end;
    padding: 8px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background: var(--bg-base);
  }

  .control-field {
    display: flex;
    flex-direction: column;
    min-width: 0;
    padding: 0;
  }

  .control-label {
    margin-bottom: 5px;
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 850;
  }

  :deep(.el-select__wrapper),
  :deep(.el-input__wrapper) {
    min-height: 34px;
    border-radius: var(--radius-sm);
    background: var(--bg-card);
    box-shadow: 0 0 0 1px var(--border-light) inset;
    transition: box-shadow var(--transition-fast), background-color var(--transition-fast);

    &:hover {
      box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.24) inset;
    }

    &.is-focus {
      box-shadow: 0 0 0 1px var(--primary-color) inset, 0 0 0 3px var(--primary-light) !important;
    }
  }

  :deep(.el-input-number .el-input__wrapper) {
    padding-left: 10px;
    padding-right: 32px;
  }

  :deep(.el-input-number__decrease),
  :deep(.el-input-number__increase) {
    width: 24px;
    border-radius: 0;
    background: var(--bg-hover);
  }

  .direction-segment {
    width: 100%;

    :deep(.el-radio-button) {
      width: 50%;
    }

    :deep(.el-radio-button__inner) {
      width: 100%;
      height: 34px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--radius-sm) !important;
      background: var(--bg-card);
      border-color: var(--border-light);
      box-shadow: none;
      font-size: 12px;
      font-weight: 800;
      transition: color var(--transition-fast), background-color var(--transition-fast), border-color var(--transition-fast);
    }

    :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
      color: white;
      background: var(--primary-color);
      border-color: var(--primary-color);
      box-shadow: none;
    }
  }

  :deep(.el-input-number) {
    width: 100%;
  }

  .screen-results {
    display: flex;
    flex-direction: column;
    gap: 18px;

    .result-section {
      padding: 14px;
      border: 1px solid var(--border-light);
      border-radius: var(--radius-base);
      background: var(--bg-card);

      .result-header {
        margin-bottom: 12px;
        .result-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 15px;
          font-weight: 800;
          .up-icon { color: var(--success-color); }
          .down-icon { color: var(--danger-color); }
        }
      }
    }
  }

  @media (max-width: 1180px) {
    .condition-rule {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 720px) {
    .screen-builder-header {
      flex-direction: column;
      align-items: stretch;
    }

    .screen-builder-actions {
      justify-content: flex-start;
    }

    .condition-controls {
      grid-template-columns: 1fr;
    }
  }
}
</style>
