<template>
  <div class="screen-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">{{ $t('screen.title') }}</span>
          <el-icon v-if="loading" class="is-loading" size="16"><Loading /></el-icon>
        </div>
      </template>

      <!-- 筛选条件区域 -->
      <div class="screen-conditions">
        <div class="condition-row">
          <!-- 连续上涨筛选 -->
          <div class="condition-box up-box">
            <div class="condition-header">
              <el-icon class="up-icon"><ArrowUp /></el-icon>
              <span class="condition-title">连续上涨</span>
            </div>
            <div class="condition-body">
              <el-form :model="upForm" inline class="screen-form">
                <el-form-item label="最少天数">
                  <el-input-number v-model="upForm.minDays" :min="1" :max="30" size="small" />
                </el-form-item>
                <el-form-item label="累计涨幅(%)">
                  <el-input-number v-model="upForm.minPct" :min="0.1" :max="50" :step="0.1" size="small" />
                </el-form-item>
              </el-form>
            </div>
          </div>

          <!-- 连续下跌筛选 -->
          <div class="condition-box down-box">
            <div class="condition-header">
              <el-icon class="down-icon"><ArrowDown /></el-icon>
              <span class="condition-title">连续下跌</span>
            </div>
            <div class="condition-body">
              <el-form :model="downForm" inline class="screen-form">
                <el-form-item label="最少天数">
                  <el-input-number v-model="downForm.minDays" :min="1" :max="30" size="small" />
                </el-form-item>
                <el-form-item label="累计跌幅(%)">
                  <el-input-number v-model="downForm.minPct" :min="0.1" :max="50" :step="0.1" size="small" />
                </el-form-item>
              </el-form>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-row">
          <el-button type="primary" size="default" @click="handleScreenBoth" :loading="loading">
            <el-icon><Search /></el-icon>
            同时查询
          </el-button>
          <el-button type="success" size="default" @click="handleScreenUp" :loading="loadingUp">
            <el-icon><ArrowUp /></el-icon>
            仅查上涨
          </el-button>
          <el-button type="danger" size="default" @click="handleScreenDown" :loading="loadingDown">
            <el-icon><ArrowDown /></el-icon>
            仅查下跌
          </el-button>
        </div>
      </div>

      <el-divider v-if="upResults.length > 0 || downResults.length > 0" />

      <!-- 空状态 -->
      <el-empty v-if="upResults.length === 0 && downResults.length === 0 && !loading && !loadingUp && !loadingDown" :description="$t('compare.emptyTip')">
        <template #description>
          <p>设置筛选条件后点击查询按钮</p>
        </template>
      </el-empty>

      <!-- 对比结果 -->
      <div v-else class="screen-results">
        <!-- 连续上涨结果 -->
        <div v-if="upResults.length > 0" class="result-section">
          <div class="result-header">
            <div class="result-title">
              <el-icon class="up-icon"><ArrowUp /></el-icon>
              <span>连续上涨基金</span>
              <el-tag type="success" size="small" effect="dark">{{ upResults.length }}</el-tag>
            </div>
          </div>
          <ResultTable 
            :data="upResults" 
            :loading="loadingUp"
            direction="up"
            @view="viewFund"
            @add="addToWatchlist"
          />
        </div>

        <!-- 连续下跌结果 -->
        <div v-if="downResults.length > 0" class="result-section">
          <div class="result-header">
            <div class="result-title">
              <el-icon class="down-icon"><ArrowDown /></el-icon>
              <span>连续下跌基金</span>
              <el-tag type="danger" size="small" effect="dark">{{ downResults.length }}</el-tag>
            </div>
          </div>
          <ResultTable 
            :data="downResults" 
            :loading="loadingDown"
            direction="down"
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

import { reactive, ref } from 'vue'
import { Loading, ArrowUp, ArrowDown, Search } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/fundStore'
import FundChart from '@/components/Charts/FundChart.vue'
import ResultTable from './components/ResultTable.vue'
import { fundApi, type FundTrendResult } from '@/api/fund'

const { t } = useI18n()
const fundStore = useFundStore()

// 上涨筛选条件
const upForm = reactive({
  minDays: 2,
  minPct: 3
})

// 下跌筛选条件
const downForm = reactive({
  minDays: 2,
  minPct: 3
})

// 结果数据
const upResults = ref<FundTrendResult[]>([])
const downResults = ref<FundTrendResult[]>([])
const loadingUp = ref(false)
const loadingDown = ref(false)
const loading = ref(false)

// 图表弹窗
const chartVisible = ref(false)
const selectedFund = ref<FundTrendResult | null>(null)

// 查询连续上涨
const handleScreenUp = async () => {
  if (fundStore.fundList.length === 0) {
    ElMessage.warning('基金列表为空，请先加载基金数据')
    return
  }

  loadingUp.value = true
  try {
    const codes = [...fundStore.fundList]
    const result = await fundApi.screen(
      'up',
      upForm.minDays,
      upForm.minPct / 100,
      codes
    )

    upResults.value = result.funds || []

    if (upResults.value.length === 0) {
      ElMessage.info('未找到符合条件的上涨基金')
    } else {
      ElMessage.success(`找到 ${upResults.value.length} 只连续上涨基金`)
    }
  } catch (error) {
    console.error('筛选失败:', error)
    ElMessage.error('筛选失败: ' + (error instanceof Error ? error.message : '未知错误'))
  } finally {
    loadingUp.value = false
  }
}

// 查询连续下跌
const handleScreenDown = async () => {
  if (fundStore.fundList.length === 0) {
    ElMessage.warning('基金列表为空，请先加载基金数据')
    return
  }

  loadingDown.value = true
  try {
    const codes = [...fundStore.fundList]
    const result = await fundApi.screen(
      'down',
      downForm.minDays,
      downForm.minPct / 100,
      codes
    )

    downResults.value = result.funds || []

    if (downResults.value.length === 0) {
      ElMessage.info('未找到符合条件的下跌基金')
    } else {
      ElMessage.success(`找到 ${downResults.value.length} 只连续下跌基金`)
    }
  } catch (error) {
    console.error('筛选失败:', error)
    ElMessage.error('筛选失败: ' + (error instanceof Error ? error.message : '未知错误'))
  } finally {
    loadingDown.value = false
  }
}

// 同时查询上涨和下跌
const handleScreenBoth = async () => {
  if (fundStore.fundList.length === 0) {
    ElMessage.warning('基金列表为空，请先加载基金数据')
    return
  }

  loading.value = true
  loadingUp.value = true
  loadingDown.value = true

  try {
    const codes = [...fundStore.fundList]
    
    // 同时发起两个请求
    const [upResult, downResult] = await Promise.all([
      fundApi.screen('up', upForm.minDays, upForm.minPct / 100, codes),
      fundApi.screen('down', downForm.minDays, downForm.minPct / 100, codes)
    ])

    upResults.value = upResult.funds || []
    downResults.value = downResult.funds || []

    const totalCount = upResults.value.length + downResults.value.length
    
    if (totalCount === 0) {
      ElMessage.info('未找到符合条件的基金')
    } else {
      ElMessage.success(`查询完成：${upResults.value.length} 只上涨，${downResults.value.length} 只下跌`)
    }
  } catch (error) {
    console.error('筛选失败:', error)
    ElMessage.error('筛选失败: ' + (error instanceof Error ? error.message : '未知错误'))
  } finally {
    loading.value = false
    loadingUp.value = false
    loadingDown.value = false
  }
}

// 查看基金图表
const viewFund = (fund: FundTrendResult) => {
  selectedFund.value = fund
  chartVisible.value = true
}

// 添加到关注列表
const addToWatchlist = async (fund: FundTrendResult) => {
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
      gap: 16px;
      margin-bottom: 16px;

      .condition-box {
        flex: 1;
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
        }

        .condition-body {
          padding: 12px;

          .screen-form {
            :deep(.el-form-item) {
              margin-bottom: 0;
              margin-right: 16px;

              &:last-child {
                margin-right: 0;
              }

              .el-form-item__label {
                font-size: 12px;
                color: var(--text-secondary);
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
