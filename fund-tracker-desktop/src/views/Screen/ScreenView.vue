<template>
  <div class="screen-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">{{ $t('screen.title') }}</span>
          <el-icon v-if="loading" class="is-loading" size="16"><Loading /></el-icon>
        </div>
      </template>

      <el-form :model="form" inline class="screen-form">
        <el-form-item :label="$t('screen.direction')">
          <el-radio-group v-model="form.direction">
            <el-radio-button value="up">{{ $t('screen.up') }}</el-radio-button>
            <el-radio-button value="down">{{ $t('screen.down') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item :label="$t('screen.minDays')">
          <el-input-number v-model="form.minDays" :min="1" :max="30" />
        </el-form-item>

        <el-form-item :label="$t('screen.minPct')">
          <el-input-number v-model="form.minPct" :min="0.1" :max="50" :step="0.1" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleScreen" :loading="loading">
            {{ $t('screen.startScreen') }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <el-table :data="results" v-loading="loading" stripe height="calc(100vh - 300px)">
        <el-table-column prop="code" :label="$t('home.fundList.code')" width="120" />
        <el-table-column prop="name" :label="$t('home.fundList.name')" min-width="200" show-overflow-tooltip />
        <el-table-column prop="days" :label="$t('screen.days')" width="120" sortable />
        <el-table-column prop="pct" :label="$t('screen.totalPct')" width="150" sortable>
          <template #default="{ row }">
            <span :class="row.pct >= 0 ? 'text-success' : 'text-danger'">
              {{ row.pct >= 0 ? '+' : '' }}{{ row.pct.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewFund(row.code)">
              {{ $t('home.fundList.chart') }}
            </el-button>
            <el-button link type="success" size="small" @click="addToWatchlist(row)">
              {{ $t('home.fundList.add') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="!loading && results.length === 0" :description="$t('home.noData')" />
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
import { Loading } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useFundStore } from '@/stores/fundStore'
import FundChart from '@/components/Charts/FundChart.vue'
import { fundApi, type FundTrendResult } from '@/api/fund'

const { t } = useI18n()
const fundStore = useFundStore()

const form = reactive({
  direction: 'up' as 'up' | 'down',
  minDays: 2,
  minPct: 3
})

const results = ref<FundTrendResult[]>([])
const loading = ref(false)
const totalCount = ref(0)

// 图表弹窗
const chartVisible = ref(false)
const selectedFund = ref<FundTrendResult | null>(null)

const handleScreen = async () => {
  if (fundStore.fundList.length === 0) {
    ElMessage.warning('基金列表为空，请先加载基金数据')
    return
  }

  loading.value = true
  try {
    const codes = [...fundStore.fundList]
    console.log('筛选基金:', codes, '方向:', form.direction, '天数:', form.minDays, '幅度:', form.minPct)

    const result = await fundApi.screen(
      form.direction,
      form.minDays,
      form.minPct / 100,
      codes
    )

    console.log('筛选结果:', result)
    results.value = result.funds || []
    totalCount.value = result.count || 0

    if (results.value.length === 0) {
      ElMessage.info('未找到符合条件的基金')
    } else {
      ElMessage.success(t('screen.resultCount', { count: totalCount.value }))
    }
  } catch (error) {
    console.error('筛选失败:', error)
    ElMessage.error('筛选失败: ' + (error instanceof Error ? error.message : '未知错误'))
  } finally {
    loading.value = false
  }
}

// 查看基金图表
const viewFund = (code: string) => {
  const fund = results.value.find(f => f.code === code)
  if (fund) {
    selectedFund.value = fund
    chartVisible.value = true
  }
}

// 添加到关注列表
const addToWatchlist = async (fund: FundTrendResult) => {
  try {
    const exists = fundStore.fundList.includes(fund.code)
    if (exists) {
      ElMessage.warning(t('ocr.fundAlreadyExists'))
      return
    }

    fundStore.addFund(fund.code)
    ElMessage.success(t('ocr.addSuccess', { name: fund.name }))
  } catch {
    ElMessage.error(t('ocr.addFailed'))
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
      font-size: var(--font-size-md);
      font-weight: 600;
    }
  }

  .screen-form {
    :deep(.el-form-item) {
      margin-bottom: 0;
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
