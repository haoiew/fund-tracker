<template>
  <div class="portfolio-view">
    <!-- 统计卡片 -->
    <el-row :gutter="24" class="stats-row">
      <el-col :xs="24" :sm="12" :lg="8">
        <div class="stat-card">
          <div class="stat-icon">
            <el-icon><Wallet /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">¥{{ formatNumber(portfolioStore.totalValue) }}</div>
            <div class="stat-label">{{ $t('portfolio.totalValue') }}</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="8">
        <div class="stat-card">
          <div class="stat-icon" :class="portfolioStore.profitPositive ? 'up' : 'down'">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value" :class="portfolioStore.profitPositive ? 'text-success' : 'text-danger'">
              {{ portfolioStore.profitPositive ? '+' : '' }}¥{{ formatNumber(portfolioStore.totalProfit) }}
            </div>
            <div class="stat-label">{{ $t('portfolio.totalProfit') }}</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="8">
        <div class="stat-card">
          <div class="stat-icon" :class="portfolioStore.profitPositive ? 'up' : 'down'">
            <el-icon><Percentage /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value" :class="portfolioStore.profitPositive ? 'text-success' : 'text-danger'">
              {{ portfolioStore.profitPositive ? '+' : '' }}{{ portfolioStore.totalProfitPct.toFixed(2) }}%
            </div>
            <div class="stat-label">{{ $t('portfolio.profitRate') }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 操作栏 -->
    <el-card class="action-card" shadow="never">
      <div class="action-bar">
        <el-button type="primary" :icon="Plus" @click="showAddDialog = true">{{ $t('portfolio.addPosition') }}</el-button>
        <el-button :icon="Refresh" @click="refreshData">{{ $t('home.refresh') }}</el-button>
        <el-button
          v-if="selectedItems.length > 0"
          type="danger"
          :icon="Delete"
          @click="batchDelete"
        >
          批量删除 ({{ selectedItems.length }})
        </el-button>
      </div>
    </el-card>

    <!-- 持仓列表 -->
    <el-card class="portfolio-list-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('portfolio.myPositions') }}</span>
          <span class="subtitle">{{ $t('portfolio.positionCount', { count: portfolioStore.itemCount }) }}</span>
        </div>
      </template>

      <!-- 调试信息 - 开发完成后可删除 -->
      <div v-if="portfolioStore.error" style="padding: 20px; background: #fef0f0; color: #f56c6c; margin-bottom: 20px; border-radius: 4px;">
        <strong>数据加载错误:</strong> {{ portfolioStore.error }}
      </div>

      <div v-if="portfolioStore.items.length > 0" style="margin-bottom: 10px; color: #909399; font-size: 12px;">
        共 {{ portfolioStore.items.length }} 条数据
      </div>

      <el-table
        :data="portfolioStore.items"
        stripe
        style="width: 100%"
        v-loading="portfolioStore.loading"
        :empty-text="portfolioStore.loading ? '加载中...' : '暂无数据'"
        border
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column prop="fund_code" :label="$t('home.fundList.code')" min-width="100" sortable />
        <el-table-column prop="fund_name" :label="$t('home.fundList.name')" min-width="180" show-overflow-tooltip sortable />
        <el-table-column prop="hold_shares" :label="$t('portfolio.holdShares')" min-width="100" align="right" sortable>
          <template #default="{ row }">
            {{ formatNumber(row.hold_shares || 0) }}
          </template>
        </el-table-column>
        <el-table-column prop="cost_nav" :label="$t('portfolio.costPrice')" min-width="90" align="right" sortable>
          <template #default="{ row }">
            ¥{{ Number(row.cost_nav || 0).toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="current_nav" :label="$t('portfolio.currentNav')" min-width="90" align="right" sortable>
          <template #default="{ row }">
            <span :class="getProfitClass(row)">
              ¥{{ Number(row.current_nav || row.cost_nav || 0).toFixed(4) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="current_value" :label="$t('portfolio.currentValue')" min-width="110" align="right" sortable>
          <template #default="{ row }">
            ¥{{ formatNumber(row.current_value || row.cost_amount || 0) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit_amount" :label="$t('portfolio.profitAmount')" min-width="110" align="right" sortable>
          <template #default="{ row }">
            <span :class="(row.profit_amount || 0) >= 0 ? 'text-success' : 'text-danger'">
              {{ (row.profit_amount || 0) >= 0 ? '+' : '' }}¥{{ formatNumber(row.profit_amount || 0) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="profit_rate" :label="$t('portfolio.profitRate')" min-width="90" align="right" sortable>
          <template #default="{ row }">
            <span :class="(row.profit_rate || 0) >= 0 ? 'text-success' : 'text-danger'">
              {{ (row.profit_rate || 0) >= 0 ? '+' : '' }}{{ (row.profit_rate || 0).toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="130" align="center" fixed="right">
          <template #default="{ row }">
            <div style="display: flex; gap: 8px; justify-content: center;">
              <el-button link type="primary" size="small" @click="editItem(row)">{{ $t('common.edit') }}</el-button>
              <el-button link type="danger" size="small" @click="deleteItem(row)">{{ $t('common.delete') }}</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty
        v-if="!portfolioStore.loading && portfolioStore.items.length === 0"
        :description="portfolioStore.error ? '数据加载失败，请刷新重试' : '暂无持仓数据'"
      >
        <el-button v-if="portfolioStore.error" type="primary" @click="refreshData">重新加载</el-button>
      </el-empty>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="isEdit ? $t('portfolio.editPosition') : $t('portfolio.addPosition')"
      width="600px"
    >
      <!-- 编辑模式 - 普通表单 -->
      <el-form v-if="isEdit" :model="form" label-width="100px">
        <el-form-item :label="$t('home.fundList.code')">
          <el-input v-model="form.fund_code" :disabled="true" />
        </el-form-item>
        <el-form-item :label="$t('home.fundList.name')">
          <el-input v-model="form.fund_name" :disabled="true" />
        </el-form-item>
        <el-form-item :label="$t('portfolio.holdShares')">
          <el-input-number v-model="form.hold_shares" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item :label="$t('portfolio.costPrice')">
          <el-input-number v-model="form.cost_nav" :min="0" :precision="4" style="width: 100%" />
        </el-form-item>
      </el-form>

      <!-- 添加模式 - 选项卡 -->
      <el-tabs v-else v-model="addMode" type="border-card">
        <!-- 手动添加 -->
        <el-tab-pane label="手动添加" name="manual">
          <el-form :model="form" label-width="100px">
            <!-- 基金代码搜索 -->
            <el-form-item :label="$t('home.fundList.code')">
              <el-select
                v-model="selectedFund"
                filterable
                remote
                reserve-keyword
                placeholder="输入基金代码或名称搜索"
                :remote-method="searchFunds"
                :loading="searchLoading"
                style="width: 100%"
                @change="onFundSelect"
              >
                <el-option
                  v-for="item in searchResults"
                  :key="item.code"
                  :label="`${item.code} - ${item.name}`"
                  :value="item"
                />
              </el-select>
            </el-form-item>

            <!-- 基金名称（只读） -->
            <el-form-item :label="$t('home.fundList.name')">
              <el-input v-model="form.fund_name" :disabled="true" />
            </el-form-item>

            <!-- 昨日净值显示 -->
            <el-form-item label="昨日净值" v-if="form.previous_nav">
              <div class="previous-nav-display">
                <span class="nav-value">{{ form.previous_nav.toFixed(4) }}</span>
                <el-tag size="small" type="info">已自动填入成本价</el-tag>
              </div>
            </el-form-item>

            <el-form-item :label="$t('portfolio.holdShares')">
              <el-input-number v-model="form.hold_shares" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
            <el-form-item :label="$t('portfolio.costPrice')">
              <el-input-number v-model="form.cost_nav" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- OCR识别 -->
        <el-tab-pane label="OCR识别导入" name="ocr">
          <div class="ocr-section">
            <div class="ocr-description">
              <el-alert
                title="支持识别图片中的基金持仓信息"
                description="请上传包含基金代码、份额、成本等信息的截图，系统将自动识别并填充"
                type="info"
                :closable="false"
                show-icon
              />
            </div>

            <!-- 图片上传 -->
            <el-upload
              class="ocr-uploader"
              drag
              action="#"
              :auto-upload="false"
              :on-change="handleImageChange"
              :show-file-list="false"
              accept="image/*"
            >
              <el-icon class="el-icon--upload"><Upload /></el-icon>
              <div class="el-upload__text">
                拖拽图片到此处或 <em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持 jpg/png 格式图片
                </div>
              </template>
            </el-upload>

            <!-- 预览和识别结果 -->
            <div v-if="ocrImageUrl" class="ocr-preview-section">
              <div class="ocr-image-preview">
                <img :src="ocrImageUrl" alt="预览" />
              </div>

              <!-- 识别结果 -->
              <div v-if="ocrResults.length > 0" class="ocr-results">
                <div class="ocr-results-header">
                  <span>识别结果 ({{ ocrResults.length }}条)</span>
                  <el-button type="primary" size="small" @click="addAllOcrResults">
                    全部添加
                  </el-button>
                </div>
                <el-table :data="ocrResults" size="small" border>
                  <el-table-column prop="fund_code" label="基金代码" width="100" />
                  <el-table-column prop="fund_name" label="基金名称" min-width="150" show-overflow-tooltip />
                  <el-table-column prop="hold_shares" label="份额" width="100" align="right">
                    <template #default="{ row }">
                      {{ row.hold_shares?.toFixed(2) || '--' }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="cost_nav" label="成本价" width="100" align="right">
                    <template #default="{ row }">
                      {{ row.cost_nav?.toFixed(4) || '--' }}
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="80" align="center">
                    <template #default="{ row, $index }">
                      <el-button link type="primary" size="small" @click="addOcrResult(row, $index)">
                        添加
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>

              <!-- 识别中 -->
              <div v-if="ocrLoading" class="ocr-loading">
                <el-icon class="is-loading" size="24"><Loading /></el-icon>
                <span>正在识别...</span>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="showAddDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button v-if="isEdit || addMode === 'manual'" type="primary" @click="saveItem">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'PortfolioView'
})

import { ref, reactive, onMounted } from 'vue'
import { Plus, Refresh, Wallet, TrendCharts, TrendCharts as Percentage, Delete, Upload, Loading } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { usePortfolioStore } from '@/stores/portfolioStore'
import type { PortfolioItem } from '@/api/portfolio'
import fundApi, { type FundSearchItem } from '@/api/fund'
import ocrApi, { type OCRResult } from '@/api/ocr'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'

const { t } = useI18n()
const portfolioStore = usePortfolioStore()

const showAddDialog = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const addMode = ref('manual') // 'manual' 或 'ocr'

// 搜索相关
const searchLoading = ref(false)
const searchResults = ref<FundSearchItem[]>([])
const selectedFund = ref<FundSearchItem | null>(null)

// 批量选择相关
const selectedItems = ref<PortfolioItem[]>([])

// OCR相关
const ocrImageUrl = ref('')
const ocrLoading = ref(false)
const ocrResults = ref<OCRResult[]>([])

const form = reactive({
  fund_code: '',
  fund_name: '',
  hold_shares: 0,
  cost_amount: 0,
  cost_nav: 0,
  previous_nav: null as number | null
})

const formatNumber = (num: number | string | null | undefined): string => {
  // 转换为数字
  const value = typeof num === 'string' ? parseFloat(num) : Number(num)
  
  // 检查是否为有效数字
  if (isNaN(value) || !isFinite(value)) {
    return '0.00'
  }
  
  // 格式化为两位小数
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const getProfitClass = (row: PortfolioItem) => {
  const profit = (row.profit_amount || 0)
  if (profit > 0) return 'text-success'
  if (profit < 0) return 'text-danger'
  return ''
}

const refreshData = () => {
  portfolioStore.refreshPortfolio()
  ElMessage.success(t('common.success'))
}

// 搜索基金
const searchFunds = async (query: string) => {
  if (!query || query.length < 2) {
    searchResults.value = []
    return
  }

  searchLoading.value = true
  try {
    const results = await fundApi.search(query, 20)
    searchResults.value = results
  } catch (e) {
    console.error('搜索基金失败:', e)
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

// 选择基金
const onFundSelect = async (fund: FundSearchItem) => {
  if (!fund) return

  form.fund_code = fund.code
  form.fund_name = fund.name

  // 获取基金详情以获取昨日净值
  try {
    const fundData = await fundApi.getRealtime(fund.code)
    if (fundData && fundData.previous_nav) {
      form.previous_nav = fundData.previous_nav
      form.cost_nav = fundData.previous_nav
    } else if (fundData && fundData.estimate_nav) {
      // 如果没有昨日净值，使用估算净值
      form.cost_nav = fundData.estimate_nav
    }
  } catch (e) {
    console.error('获取基金详情失败:', e)
  }
}

const editItem = (row: PortfolioItem) => {
  isEdit.value = true
  editingId.value = row.id || null
  form.fund_code = row.fund_code
  form.fund_name = row.fund_name || ''
  form.hold_shares = row.hold_shares || 0
  form.cost_amount = row.cost_amount || 0
  form.cost_nav = row.cost_nav || 0
  form.previous_nav = null
  selectedFund.value = null
  showAddDialog.value = true
}

// 处理选择变化
const handleSelectionChange = (selection: PortfolioItem[]) => {
  selectedItems.value = selection
}

// 批量删除
const batchDelete = async () => {
  if (selectedItems.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedItems.value.length} 条持仓吗？`,
      '确认批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const ids = selectedItems.value.map(item => item.id!).filter(Boolean)
    for (const id of ids) {
      await portfolioStore.deleteItem(id)
    }

    selectedItems.value = []
    ElMessage.success(`成功删除 ${ids.length} 条持仓`)
  } catch {
    // 用户取消
  }
}

const deleteItem = async (row: PortfolioItem) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${row.fund_name} 的持仓吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await portfolioStore.deleteItem(row.id!)
    ElMessage.success('删除成功')
  } catch {
    // 用户取消
  }
}

const saveItem = async () => {
  if (!form.fund_code || !form.fund_name) {
    ElMessage.warning('请填写基金代码和名称')
    return
  }

  if (form.hold_shares <= 0) {
    ElMessage.warning('请输入有效的持有份额')
    return
  }

  if (form.cost_nav <= 0) {
    ElMessage.warning('请输入有效的成本价')
    return
  }

  // 重新计算成本金额
  const costAmount = form.cost_nav * form.hold_shares

  const itemData = {
    fund_code: form.fund_code,
    fund_name: form.fund_name,
    hold_shares: form.hold_shares,
    cost_amount: costAmount,
    cost_nav: form.cost_nav
  }

  const success = isEdit.value && editingId.value
    ? await portfolioStore.updateItem(editingId.value, itemData)
    : await portfolioStore.addItem(itemData)

  if (success) {
    ElMessage.success(isEdit.value ? '更新成功' : '添加成功')
    showAddDialog.value = false
    resetForm()
  }
}

const resetForm = () => {
  form.fund_code = ''
  form.fund_name = ''
  form.hold_shares = 0
  form.cost_amount = 0
  form.cost_nav = 0
  form.previous_nav = null
  isEdit.value = false
  editingId.value = null
  selectedFund.value = null
  searchResults.value = []
  addMode.value = 'manual'
  ocrImageUrl.value = ''
  ocrResults.value = []
}

// OCR图片上传处理
const handleImageChange = async (uploadFile: UploadFile) => {
  const file = uploadFile.raw
  if (!file) return

  // 显示预览
  ocrImageUrl.value = URL.createObjectURL(file)
  ocrLoading.value = true
  ocrResults.value = []

  try {
    const results = await ocrApi.recognize(file)
    ocrResults.value = results
    if (results.length === 0) {
      ElMessage.warning('未识别到基金信息，请尝试上传更清晰的图片')
    } else {
      ElMessage.success(`成功识别 ${results.length} 条基金信息`)
    }
  } catch (e: any) {
    console.error('OCR识别失败:', e)
    ElMessage.error(e.message || 'OCR识别失败')
  } finally {
    ocrLoading.value = false
  }
}

// 添加单条OCR结果到持仓
const addOcrResult = async (result: OCRResult, index: number) => {
  try {
    const success = await portfolioStore.addItem({
      fund_code: result.fund_code,
      fund_name: result.fund_name,
      hold_shares: result.hold_shares || 0,
      cost_nav: result.cost_nav || undefined
    })

    if (success) {
      ElMessage.success(`已添加 ${result.fund_name}`)
      // 从列表中移除
      ocrResults.value.splice(index, 1)
      // 如果全部添加完成，关闭对话框
      if (ocrResults.value.length === 0) {
        showAddDialog.value = false
        resetForm()
      }
    }
  } catch (e) {
    console.error('添加失败:', e)
    ElMessage.error('添加失败')
  }
}

// 添加所有OCR结果（并行执行）
const addAllOcrResults = async () => {
  if (ocrResults.value.length === 0) return

  const totalCount = ocrResults.value.length
  console.log(`[OCR] 开始并行添加 ${totalCount} 条持仓...`)
  const startTime = Date.now()

  // 并行添加所有持仓（利用乐观更新，瞬间完成）
  const promises = ocrResults.value.map(async (result, index) => {
    try {
      const success = await portfolioStore.addItem({
        fund_code: result.fund_code,
        fund_name: result.fund_name,
        hold_shares: result.hold_shares || 0,
        cost_nav: result.cost_nav || undefined
      })
      return { success, index, fund_code: result.fund_code }
    } catch (e) {
      return { success: false, index, fund_code: result.fund_code }
    }
  })

  // 等待所有添加完成
  const results = await Promise.all(promises)

  const successCount = results.filter(r => r.success).length
  const failCount = results.filter(r => !r.success).length

  // 移除成功添加的项（从后往前移除，避免索引变化）
  const successIndices = results
    .filter(r => r.success)
    .map(r => r.index)
    .sort((a, b) => b - a)

  for (const index of successIndices) {
    ocrResults.value.splice(index, 1)
  }

  const elapsed = Date.now() - startTime
  console.log(`[OCR] 并行添加完成: ${successCount} 成功, ${failCount} 失败, 耗时: ${elapsed}ms`)

  if (successCount > 0) {
    ElMessage.success(`成功添加 ${successCount} 条持仓`)
  }
  if (failCount > 0) {
    ElMessage.warning(`${failCount} 条添加失败`)
  }

  if (ocrResults.value.length === 0) {
    showAddDialog.value = false
    resetForm()
  }
}

onMounted(() => {
  // 数据已由 MainLayout.vue 中的 dataManager.initialize() 统一加载
  // 这里不需要重复加载
  console.log('[PortfolioView] 页面已挂载，数据由 DataManager 统一管理')
})
</script>

<style scoped lang="scss">
.portfolio-view {
  .stats-row {
    margin-bottom: 24px;
  }

  .stat-card {
    background: var(--bg-base);
    border-radius: 16px;
    padding: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: var(--shadow-light);

    .stat-icon {
      width: 56px;
      height: 56px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      background: rgba(64, 158, 255, 0.1);
      color: var(--primary-color);

      &.up {
        background: rgba(103, 194, 58, 0.1);
        color: var(--success-color);
      }

      &.down {
        background: rgba(245, 108, 108, 0.1);
        color: var(--danger-color);
      }
    }

    .stat-info {
      .stat-value {
        font-size: 28px;
        font-weight: 700;
      }

      .stat-label {
        font-size: 14px;
        color: var(--text-secondary);
        margin-top: 4px;
      }
    }
  }

  .action-card {
    margin-bottom: 24px;
    border-radius: var(--radius-lg);
  }

  .portfolio-list-card {
    border-radius: var(--radius-lg);

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .subtitle {
        font-size: 14px;
        color: var(--text-secondary);
        font-weight: normal;
      }
    }
  }

  .text-success {
    color: var(--success-color);
  }

  .text-danger {
    color: var(--danger-color);
  }

  .previous-nav-display {
    display: flex;
    align-items: center;
    gap: 12px;

    .nav-value {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
    }
  }

  // OCR 样式
  .ocr-section {
    .ocr-description {
      margin-bottom: 20px;
    }

    .ocr-uploader {
      :deep(.el-upload-dragger) {
        width: 100%;
        height: 150px;
      }
    }

    .ocr-preview-section {
      margin-top: 20px;

      .ocr-image-preview {
        margin-bottom: 16px;
        border-radius: var(--radius-base);
        overflow: hidden;
        border: 1px solid var(--border-color);

        img {
          width: 100%;
          max-height: 200px;
          object-fit: contain;
          display: block;
        }
      }

      .ocr-results {
        .ocr-results-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
          font-weight: 500;
        }
      }

      .ocr-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 20px;
        color: var(--text-secondary);
      }
    }
  }
}
</style>
