<template>
  <div class="screen-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">{{ $t('screen.title') }}</span>
          <el-button type="primary" size="small" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            添加筛选
          </el-button>
        </div>
      </template>

      <!-- 筛选条件区域 -->
      <div v-if="conditions.length > 0" class="screen-conditions">
        <div class="condition-row">
          <div
            v-for="condition in conditions"
            :key="condition.id"
            class="condition-box"
            :class="condition.direction === 'up' ? 'up-box' : 'down-box'"
          >
            <div class="condition-header">
              <el-icon :class="condition.direction === 'up' ? 'up-icon' : 'down-icon'">
                <component :is="condition.direction === 'up' ? ArrowUp : ArrowDown" />
              </el-icon>
              <span class="condition-title">{{ getConditionLabel(condition) }}</span>
              <div class="condition-actions">
                <el-button link size="small" @click="editCondition(condition)">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button link size="small" type="danger" @click="removeCondition(condition.id)">
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
            </div>
            <div class="condition-body">
              <div class="condition-params">
                <template v-if="condition.type === 'consecutive'">
                  <span class="param-item">
                    <span class="param-label">最少天数:</span>
                    <span class="param-value">{{ condition.minDays }}</span>
                  </span>
                  <span class="param-item">
                    <span class="param-label">{{ condition.direction === 'up' ? '涨幅' : '跌幅' }}:</span>
                    <span class="param-value">{{ (condition.minPct * 100).toFixed(1) }}%</span>
                  </span>
                </template>
                <template v-else>
                  <span class="param-item">
                    <span class="param-label">统计天数:</span>
                    <span class="param-value">{{ condition.periodDays }}</span>
                  </span>
                  <span class="param-item">
                    <span class="param-label">{{ condition.direction === 'up' ? '涨幅' : '跌幅' }}:</span>
                    <span class="param-value">{{ (condition.minPct * 100).toFixed(1) }}%</span>
                  </span>
                </template>
              </div>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-row">
          <el-button type="primary" size="default" @click="handleScreenAll" :loading="loading">
            <el-icon><Search /></el-icon>
            一键查询所有筛选条件
          </el-button>
        </div>
      </div>

      <!-- 空状态 -->
      <el-empty v-if="conditions.length === 0" description="暂无筛选条件">
        <el-button type="primary" @click="showAddDialog">添加筛选条件</el-button>
      </el-empty>

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

    <!-- 条件配置弹窗 -->
    <ConditionDialog
      v-model="dialogVisible"
      :edit-condition="editingCondition"
      @confirm="handleConditionConfirm"
    />

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
import { Plus, Edit, Close, ArrowUp, ArrowDown, Search } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/fundStore'
import FundChart from '@/components/Charts/FundChart.vue'
import ResultTable from './components/ResultTable.vue'
import ConditionDialog from './components/ConditionDialog.vue'
import { fundApi, type ScreenCondition, type ScreenResult, type ScreenType, type FundTrendResult } from '@/api/fund'

const { t } = useI18n()
const fundStore = useFundStore()

// 筛选条件列表
const conditions = ref<ScreenCondition[]>([
  {
    id: generateId(),
    type: 'consecutive',
    direction: 'up',
    minDays: 2,
    minPct: 0.03
  }
])

// 筛选结果
const results = ref<(ScreenResult & { loading: boolean })[]>([])

// 加载状态
const loading = ref(false)

// 弹窗控制
const dialogVisible = ref(false)
const editingCondition = ref<ScreenCondition | null>(null)

// 图表弹窗
const chartVisible = ref(false)
const selectedFund = ref<FundTrendResult | null>(null)

// 生成唯一ID
function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2, 9)
}

// 获取条件标签
function getConditionLabel(condition: ScreenCondition): string {
  const typeLabel = condition.type === 'consecutive' ? '连续' : `${condition.periodDays}天内`
  const directionLabel = condition.direction === 'up' ? '上涨' : '下跌'
  return `${typeLabel}${directionLabel}`
}

// 根据ID获取条件标签
function getConditionLabelById(conditionId: string): string {
  const condition = conditions.value.find(c => c.id === conditionId)
  return condition ? getConditionLabel(condition) : '未知筛选'
}

// 根据ID获取筛选类型
function getConditionTypeById(conditionId: string): ScreenType {
  const condition = conditions.value.find(c => c.id === conditionId)
  return condition?.type ?? 'consecutive'
}

// 显示添加弹窗
function showAddDialog() {
  editingCondition.value = null
  dialogVisible.value = true
}

// 编辑条件
function editCondition(condition: ScreenCondition) {
  editingCondition.value = condition
  dialogVisible.value = true
}

// 删除条件
function removeCondition(id: string) {
  conditions.value = conditions.value.filter(c => c.id !== id)
  results.value = results.value.filter(r => r.conditionId !== id)
}

// 处理条件确认
function handleConditionConfirm(conditionData: Omit<ScreenCondition, 'id'>) {
  if (editingCondition.value) {
    // 编辑模式
    const index = conditions.value.findIndex(c => c.id === editingCondition.value!.id)
    if (index !== -1) {
      conditions.value[index] = { ...conditionData, id: editingCondition.value.id }
    }
  } else {
    // 添加模式
    conditions.value.push({ ...conditionData, id: generateId() })
  }
  editingCondition.value = null
}

// 一键查询所有筛选条件
async function handleScreenAll() {
  if (fundStore.fundList.length === 0) {
    ElMessage.warning('基金列表为空，请先加载基金数据')
    return
  }

  if (conditions.value.length === 0) {
    ElMessage.warning('请先添加筛选条件')
    return
  }

  loading.value = true
  const codes = [...fundStore.fundList]

  // 初始化结果数组
  results.value = conditions.value.map(c => ({
    conditionId: c.id,
    direction: c.direction,
    count: 0,
    funds: [],
    loading: true
  }))

  try {
    // 并发执行所有筛选
    const promises = conditions.value.map(async (condition) => {
      try {
        if (condition.type === 'consecutive') {
          const result = await fundApi.screen(
            condition.direction,
            condition.minDays!,
            condition.minPct,
            codes
          )
          return {
            conditionId: condition.id,
            direction: condition.direction,
            count: result.count,
            funds: result.funds,
            loading: false
          }
        } else {
          const result = await fundApi.screenPeriod(
            condition.direction,
            condition.periodDays!,
            condition.minPct,
            codes
          )
          return {
            conditionId: condition.id,
            direction: condition.direction,
            count: result.count,
            funds: result.funds,
            loading: false
          }
        }
      } catch (error) {
        console.error(`筛选失败 [${getConditionLabel(condition)}]:`, error)
        return {
          conditionId: condition.id,
          direction: condition.direction,
          count: 0,
          funds: [],
          loading: false
        }
      }
    })

    const allResults = await Promise.all(promises)
    results.value = allResults

    const totalCount = allResults.reduce((sum, r) => sum + r.count, 0)
    if (totalCount === 0) {
      ElMessage.info('未找到符合条件的基金')
    } else {
      ElMessage.success(`查询完成，共找到 ${totalCount} 只基金`)
    }
  } catch (error) {
    console.error('筛选失败:', error)
    ElMessage.error('筛选失败: ' + (error instanceof Error ? error.message : '未知错误'))
  } finally {
    loading.value = false
  }
}

// 查看基金图表
function viewFund(fund: FundTrendResult) {
  selectedFund.value = fund
  chartVisible.value = true
}

// 添加到关注列表
async function addToWatchlist(fund: FundTrendResult) {
  try {
    const exists = fundStore.fundList.includes(fund.code)
    if (exists) {
      ElMessage.warning(t('fund.alreadyInWatchlist'))
      return
    }

    fundStore.addFund(fund.code)
    ElMessage.success(t('fund.addSuccess', { name: fund.name }))
  } catch {
    ElMessage.error(t('fund.addFailed'))
  }
}
</script>

<style scoped lang="scss">
.screen-view {
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;

    .title {
      font-size: 16px;
      font-weight: 600;
    }
  }

  // 筛选条件区域
  .screen-conditions {
    .condition-row {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      margin-bottom: 16px;

      .condition-box {
        flex: 0 1 calc(50% - 8px);
        min-width: 240px;
        border-radius: 8px;
        border: 1px solid var(--border-light);
        overflow: hidden;

        &.up-box {
          border-color: rgba(239, 68, 68, 0.3);
          background: rgba(239, 68, 68, 0.05);

          .condition-header {
            background: rgba(239, 68, 68, 0.1);
          }
        }

        &.down-box {
          border-color: rgba(16, 185, 129, 0.3);
          background: rgba(16, 185, 129, 0.05);

          .condition-header {
            background: rgba(16, 185, 129, 0.1);
          }
        }

        .condition-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          font-weight: 600;
          font-size: 14px;

          .up-icon {
            color: var(--danger-color);
          }

          .down-icon {
            color: var(--success-color);
          }

          .condition-title {
            flex: 1;
          }

          .condition-actions {
            display: flex;
            gap: 4px;
          }
        }

        .condition-body {
          padding: 12px;

          .condition-params {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;

            .param-item {
              display: flex;
              align-items: center;
              gap: 4px;

              .param-label {
                font-size: 12px;
                color: var(--text-secondary);
              }

              .param-value {
                font-weight: 600;
                font-size: 14px;
              }
            }
          }
        }
      }
    }

    .action-row {
      display: flex;
      justify-content: center;
      gap: 12px;
      padding-top: 8px;
    }
  }

  // 结果区域
  .screen-results {
    .result-section {
      margin-bottom: 24px;

      &:last-child {
        margin-bottom: 0;
      }

      .result-header {
        margin-bottom: 12px;

        .result-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 15px;
          font-weight: 600;

          .up-icon {
            color: var(--danger-color);
          }

          .down-icon {
            color: var(--success-color);
          }
        }
      }
    }
  }
}
</style>
