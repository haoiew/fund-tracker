<template>
  <div class="screen-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">{{ $t('screen.title') }}</span>
          <el-button type="primary" size="small" @click="addCondition">
            <el-icon><Plus /></el-icon>
            添加筛选
          </el-button>
        </div>
      </template>

      <!-- 筛选条件区域 -->
      <div class="screen-conditions">
        <div class="condition-row">
          <div
            v-for="(condition, index) in conditions"
            :key="condition.id"
            class="condition-box"
            :class="condition.direction === 'up' ? 'up-box' : 'down-box'"
          >
            <div class="condition-header">
              <el-icon :class="condition.direction === 'up' ? 'up-icon' : 'down-icon'">
                <component :is="condition.direction === 'up' ? ArrowUp : ArrowDown" />
              </el-icon>
              <span class="condition-title">{{ getConditionLabel(condition) }}</span>
              <el-button
                v-if="conditions.length > 1"
                link
                size="small"
                type="danger"
                @click="removeCondition(condition.id)"
              >
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
            <div class="condition-body">
              <el-form inline class="condition-form">
                <el-form-item label="类型">
                  <el-select v-model="condition.type" size="small" style="width: 110px">
                    <el-option label="连续涨跌" value="consecutive" />
                    <el-option label="N天内累计" value="period" />
                  </el-select>
                </el-form-item>
                <el-form-item label="方向">
                  <el-radio-group v-model="condition.direction" size="small">
                    <el-radio-button value="up">涨</el-radio-button>
                    <el-radio-button value="down">跌</el-radio-button>
                  </el-radio-group>
                </el-form-item>
                <template v-if="condition.type === 'consecutive'">
                  <el-form-item label="最少天数">
                    <el-input-number
                      v-model="condition.minDays"
                      :min="1"
                      :max="30"
                      size="small"
                      controls-position="right"
                      style="width: 80px"
                    />
                  </el-form-item>
                </template>
                <template v-else>
                  <el-form-item label="统计天数">
                    <el-input-number
                      v-model="condition.periodDays"
                      :min="1"
                      :max="90"
                      size="small"
                      controls-position="right"
                      style="width: 80px"
                    />
                  </el-form-item>
                </template>
                <el-form-item label="涨跌幅(%)">
                  <el-input-number
                    v-model="condition.minPctDisplay"
                    :min="0.1"
                    :max="50"
                    :step="0.5"
                    :precision="1"
                    size="small"
                    controls-position="right"
                    style="width: 80px"
                  />
                </el-form-item>
              </el-form>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-row">
          <el-button type="primary" size="default" @click="handleScreenAll" :loading="loading">
            <el-icon><Search /></el-icon>
            一键查询
          </el-button>
          <el-tooltip content="开启后将今日实时估值纳入涨跌幅计算" placement="top">
            <el-switch
              v-model="includeRealtime"
              active-text="含实时估值"
              inactive-text=""
              style="margin-left: 16px"
            />
          </el-tooltip>
        </div>
      </div>

      <el-divider v-if="results.length > 0" />

      <!-- 筛选结果 -->
      <div v-if="results.length > 0" class="screen-results">
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
            :direction="result.direction as 'up' | 'down'"
            :screen-type="getConditionTypeById(result.conditionId)"
            @view="viewFund"
            @add="addToWatchlist"
          />
        </div>
      </div>
    </el-card>

    <!-- 基金图表弹窗 -->
    <el-dialog
      v-model="chartVisible"
      :title="$t('fund.chartTitle')"
      width="900px"
      destroy-on-close
      align-center
    >
      <FundChart v-if="selectedFund" :code="selectedFund.code" :name="selectedFund.name" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'ScreenView'
})

import { ref } from 'vue'
import { Plus, Close, ArrowUp, ArrowDown, Search } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/fundStore'
import FundChart from '@/components/Charts/FundChart.vue'
import ResultTable from './components/ResultTable.vue'
import { fundApi, type ScreenType, type FundTrendResult } from '@/api/fund'

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
  direction: string
  count: number
  funds: FundTrendResult[]
  loading: boolean
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
const includeRealtime = ref(false)
const chartVisible = ref(false)
const selectedFund = ref<FundTrendResult | null>(null)

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

async function handleScreenAll() {
  if (fundStore.fundList.length === 0) {
    ElMessage.warning('基金列表为空，请先加载基金数据')
    return
  }

  loading.value = true
  const codes = [...fundStore.fundList]

  results.value = conditions.value.map(c => ({
    conditionId: c.id,
    direction: c.direction,
    count: 0,
    funds: [],
    loading: true
  }))

  try {
    const promises = conditions.value.map(async (condition) => {
      try {
        const minPct = condition.minPctDisplay / 100
        if (condition.type === 'consecutive') {
          const result = await fundApi.screen(condition.direction, condition.minDays, minPct, codes, includeRealtime.value)
          return { conditionId: condition.id, direction: condition.direction, count: result.count, funds: result.funds, loading: false }
        } else {
          const result = await fundApi.screenPeriod(condition.direction, condition.periodDays, minPct, codes, includeRealtime.value)
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
      ElMessage.success(`查询完成，共找到 ${totalCount} 只基金`)
    }
  } catch (error) {
    ElMessage.error('筛选失败')
  } finally {
    loading.value = false
  }
}

function viewFund(fund: FundTrendResult) {
  selectedFund.value = fund
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
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .title {
      font-size: 16px;
      font-weight: 600;
    }
  }

  .screen-conditions {
    .condition-row {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      margin-bottom: 16px;

      .condition-box {
        flex: 1 1 calc(50% - 8px);
        min-width: 360px;
        border-radius: 8px;
        border: 1px solid var(--border-light);
        overflow: hidden;

        &.up-box {
          border-color: rgba(239, 68, 68, 0.3);
          background: rgba(239, 68, 68, 0.05);
          .condition-header { background: rgba(239, 68, 68, 0.1); }
        }

        &.down-box {
          border-color: rgba(16, 185, 129, 0.3);
          background: rgba(16, 185, 129, 0.05);
          .condition-header { background: rgba(16, 185, 129, 0.1); }
        }

        .condition-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          font-weight: 600;
          font-size: 14px;

          .up-icon { color: var(--danger-color); }
          .down-icon { color: var(--success-color); }
          .condition-title { flex: 1; }
        }

        .condition-body {
          padding: 12px;

          .condition-form {
            display: flex;
            flex-wrap: wrap;
            gap: 0;

            :deep(.el-form-item) {
              margin-bottom: 8px;
              margin-right: 12px;
              &:last-child { margin-right: 0; }
              .el-form-item__label {
                font-size: 12px;
                color: var(--text-secondary);
                padding-right: 4px;
              }
            }
          }
        }
      }
    }

    .action-row {
      display: flex;
      justify-content: center;
      padding-top: 4px;
    }
  }

  .screen-results {
    .result-section {
      margin-bottom: 24px;
      &:last-child { margin-bottom: 0; }

      .result-header {
        margin-bottom: 12px;
        .result-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 15px;
          font-weight: 600;
          .up-icon { color: var(--danger-color); }
          .down-icon { color: var(--success-color); }
        }
      }
    }
  }
}
</style>
