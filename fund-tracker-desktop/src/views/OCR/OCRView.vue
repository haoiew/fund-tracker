<template>
  <div class="ocr-view">
    <!-- 上传区域 -->
    <el-card shadow="never" class="upload-card">
      <template #header>
        <div class="card-header">
          <span class="title">{{ $t('ocr.title') }}</span>
          <el-tooltip :content="$t('ocr.tip')" placement="top">
            <el-icon size="16" class="tip-icon"><InfoFilled /></el-icon>
          </el-tooltip>
        </div>
      </template>

      <!-- 拖拽上传区域 -->
      <div
        class="upload-area"
        :class="{ 'is-dragover': isDragOver, 'has-image': previewImage }"
        @dragenter.prevent="handleDragEnter"
        @dragleave.prevent="handleDragLeave"
        @dragover.prevent
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          style="display: none"
          @change="handleFileChange"
        />

        <!-- 未上传状态 -->
        <template v-if="!previewImage">
          <div class="upload-placeholder">
            <el-icon size="48" class="upload-icon"><Picture /></el-icon>
            <p class="upload-text">{{ $t('ocr.dragTip') }}</p>
            <p class="upload-subtext">{{ $t('ocr.supportFormat') }}</p>
            <el-button type="primary" size="small">{{ $t('ocr.selectFile') }}</el-button>
          </div>
        </template>

        <!-- 已上传预览 -->
        <template v-else>
          <div class="preview-container">
            <img :src="previewImage" alt="预览" class="preview-image" />
            <div class="preview-actions">
              <el-button type="danger" size="small" @click.stop="clearImage">
                <el-icon><Delete /></el-icon>
                {{ $t('common.delete') }}
              </el-button>
              <el-button type="primary" size="small" :loading="isProcessing" @click.stop="processImage">
                <el-icon><View /></el-icon>
                {{ isProcessing ? $t('ocr.processing') : $t('ocr.startRecognize') }}
              </el-button>
            </div>
          </div>
        </template>
      </div>
    </el-card>

    <!-- 识别结果 - 持仓列表 -->
    <el-card v-if="extractedPositions.length > 0" shadow="never" class="result-card" v-loading="isProcessing">
      <template #header>
        <div class="card-header">
          <span class="title">识别到的持仓</span>
          <div class="header-actions">
            <el-tag v-if="extractedPositions.length > 0" type="success" size="small">
              共 {{ extractedPositions.length }} 只基金
            </el-tag>
            <el-tag v-if="matchedCount > 0" type="primary" size="small" style="margin-left: 8px;">
              已匹配 {{ matchedCount }} 只
            </el-tag>
            <el-button
              v-if="extractedPositions.length > 0"
              type="primary"
              size="small"
              :loading="isImporting"
              @click="importAllPositions"
              style="margin-left: 12px;"
            >
              <el-icon><Plus /></el-icon>
              {{ isImporting ? '导入中...' : '导入全部' }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- 持仓表格 -->
      <el-table :data="extractedPositions" stripe size="small" class="position-table">
        <el-table-column type="index" width="50" />
        <el-table-column prop="fund_name" label="基金名称" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="fund-name-cell">
              <span :class="{ 'unmatched': !row.fund_code }">{{ row.fund_name }}</span>
              <el-tag v-if="!row.fund_code" type="warning" size="small" effect="plain">未匹配</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="fund_code" label="基金代码" width="100">
          <template #default="{ row }">
            <span v-if="row.fund_code">{{ row.fund_code }}</span>
            <el-input v-else v-model="row.manual_code" size="small" placeholder="输入代码" style="width: 90px;"></el-input>
          </template>
        </el-table-column>
        <el-table-column prop="market_value" label="当前市值" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.market_value">¥{{ formatNumber(row.market_value) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="profit_amount" label="持有收益" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.profit_amount" :class="row.profit_amount >= 0 ? 'text-success' : 'text-danger'">
              {{ row.profit_amount >= 0 ? '+' : '' }}¥{{ formatNumber(row.profit_amount) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="profit_rate" label="收益率" width="100" align="right">
          <template #default="{ row }">
            <span v-if="row.profit_rate" :class="row.profit_rate >= 0 ? 'text-success' : 'text-danger'">
              {{ (row.profit_rate * 100).toFixed(2) }}%
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row, $index }">
            <el-button
              v-if="row.fund_code || row.manual_code"
              link
              type="primary"
              size="small"
              @click="importPosition(row, $index)"
            >
              导入
            </el-button>
            <el-button link type="danger" size="small" @click="removePosition($index)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 导入说明 -->
      <div class="import-tips">
        <el-alert
          type="info"
          :closable="false"
          show-icon
        >
          <template #title>
            导入说明
          </template>
          <div class="tips-content">
            <p>1. 系统会自动识别基金名称、市值、收益等信息</p>
            <p>2. 未匹配的基金需要手动输入6位基金代码</p>
            <p>3. 导入后会自动计算持有份额和成本净值</p>
            <p>4. 建议核对识别结果后再批量导入</p>
          </div>
        </el-alert>
      </div>
    </el-card>

    <!-- 原始识别文本 -->
    <el-card v-if="rawText" shadow="never" class="raw-text-card">
      <template #header>
        <div class="card-header">
          <span class="title">原始识别文本</span>
        </div>
      </template>
      <el-input
        v-model="rawText"
        type="textarea"
        :rows="6"
        readonly
        class="raw-text-area"
      ></el-input>
    </el-card>

    <!-- 使用说明 -->
    <el-card shadow="never" class="help-card">
      <template #header>
        <div class="card-header">
          <span class="title">{{ $t('ocr.howToUse') }}</span>
        </div>
      </template>
      <el-steps :active="1" simple>
        <el-step :title="$t('ocr.step1')" :icon="Picture" />
        <el-step :title="$t('ocr.step2')" :icon="Upload" />
        <el-step :title="$t('ocr.step3')" :icon="View" />
      </el-steps>
    </el-card>

    <!-- 基金详情弹窗 -->
    <el-dialog
      v-model="chartVisible"
      :title="$t('fund.chartTitle')"
      width="900px"
      destroy-on-close
      align-center
    >
      <FundChart v-if="selectedFundCode" :code="selectedFundCode" :name="selectedFundName"></FundChart>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Picture, Delete, View, InfoFilled, Upload, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { useFundStore } from '@/stores/fundStore'
import { usePortfolioStore } from '@/stores/portfolioStore'
import ocrApi, { type OcrPosition } from '@/api/ocr'
import FundChart from '@/components/Charts/FundChart.vue'

const { t } = useI18n()
const fundStore = useFundStore()
const portfolioStore = usePortfolioStore()

// 状态
const fileInput = ref<HTMLInputElement>()
const isDragOver = ref(false)
const previewImage = ref<string>('')
const imageBase64 = ref<string>('')
const isProcessing = ref(false)
const isImporting = ref(false)
const extractedPositions = ref<(OcrPosition & { manual_code?: string })[]>([])
const rawText = ref<string>('')

// 图表弹窗
const chartVisible = ref(false)
const selectedFundCode = ref('')
const selectedFundName = ref('')

// 计算属性
const matchedCount = computed(() => {
  return extractedPositions.value.filter(p => p.fund_code).length
})

// 拖拽处理
const handleDragEnter = () => {
  isDragOver.value = true
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (e: DragEvent) => {
  isDragOver.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0 && files[0]) {
    handleFile(files[0])
  }
}

// 文件选择
const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  const files = target.files
  if (files && files.length > 0 && files[0]) {
    handleFile(files[0])
  }
}

// 处理文件
const handleFile = (file: File) => {
  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    ElMessage.error(t('ocr.invalidFileType'))
    return
  }

  // 验证文件大小（最大10MB）
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error(t('ocr.fileTooLarge'))
    return
  }

  // 读取文件
  const reader = new FileReader()
  reader.onload = (e) => {
    const result = e.target?.result as string
    previewImage.value = result
    // 提取base64部分
    imageBase64.value = result.split(',')[1] || result
  }
  reader.readAsDataURL(file)
}

// 清除图片
const clearImage = () => {
  previewImage.value = ''
  imageBase64.value = ''
  extractedPositions.value = []
  rawText.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 处理图片识别
const processImage = async () => {
  if (!imageBase64.value) {
    ElMessage.warning(t('ocr.pleaseUploadImage'))
    return
  }

  isProcessing.value = true
  try {
    const result = await ocrApi.extractPositions(imageBase64.value)
    extractedPositions.value = result.positions || []
    rawText.value = result.raw_result?.raw_text || ''

    if (extractedPositions.value.length > 0) {
      ElMessage.success(`成功识别 ${extractedPositions.value.length} 只基金`)
    } else {
      ElMessage.warning('未识别到基金持仓信息，请尝试上传更清晰的截图')
    }
  } catch (error) {
    console.error('OCR识别失败:', error)
    ElMessage.error(t('ocr.recognizeFailed'))
  } finally {
    isProcessing.value = false
  }
}

// 删除识别的持仓
const removePosition = (index: number) => {
  extractedPositions.value.splice(index, 1)
  ElMessage.success('已删除')
}

// 导入单个持仓
const importPosition = async (position: OcrPosition & { manual_code?: string }, index: number) => {
  const code = position.fund_code || position.manual_code
  if (!code) {
    ElMessage.warning('请输入基金代码')
    return
  }

  try {
    // 检查是否已存在
    const exists = portfolioStore.items.some((p: { fund_code: string }) => p.fund_code === code)
    if (exists) {
      ElMessage.warning(`基金 ${code} 已在持仓中`)
      return
    }

    // 添加到持仓
    await portfolioStore.addItem({
      fund_code: code,
      fund_name: position.fund_name,
      hold_shares: position.hold_shares || 0,
      cost_amount: position.cost_basis || position.market_value || 0,
      cost_nav: position.cost_nav || 0
    })

    // 从列表中移除
    extractedPositions.value.splice(index, 1)
    ElMessage.success(`已导入 ${position.fund_name}`)
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败')
  }
}

// 导入全部持仓
const importAllPositions = async () => {
  // 检查是否有未匹配的基金
  const unmatched = extractedPositions.value.filter(p => !p.fund_code && !p.manual_code)
  if (unmatched.length > 0) {
    ElMessage.warning(`有 ${unmatched.length} 只基金未匹配代码，请先手动输入`)
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要导入 ${extractedPositions.value.length} 只基金到持仓管理吗？`,
      '确认导入',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    isImporting.value = true
    let successCount = 0
    let failCount = 0

    // 逐个导入
    for (const position of [...extractedPositions.value]) {
      const code = position.fund_code || position.manual_code
      if (!code) continue

      try {
        // 检查是否已存在
        const exists = portfolioStore.items.some((p: { fund_code: string }) => p.fund_code === code)
        if (exists) {
          failCount++
          continue
        }

        await portfolioStore.addItem({
          fund_code: code,
          fund_name: position.fund_name,
          hold_shares: position.hold_shares || 0,
          cost_amount: position.cost_basis || position.market_value || 0,
          cost_nav: position.cost_nav || 0
        })
        successCount++
      } catch {
        failCount++
      }
    }

    // 清空已导入的
    extractedPositions.value = []

    if (successCount > 0) {
      ElMessage.success(`成功导入 ${successCount} 只基金${failCount > 0 ? `，${failCount} 只失败` : ''}`)
    } else {
      ElMessage.warning('导入失败，请检查基金代码是否正确')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量导入失败:', error)
      ElMessage.error('批量导入失败')
    }
  } finally {
    isImporting.value = false
  }
}

// 格式化数字
const formatNumber = (num: number): string => {
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 获取置信度颜色
const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.8) return '#67c23a'
  if (confidence >= 0.5) return '#e6a23c'
  return '#f56c6c'
}

// 查看基金图表
const viewFund = (code: string) => {
  selectedFundCode.value = code
  selectedFundName.value = code
  chartVisible.value = true
}
</script>

<style scoped lang="scss">
.ocr-view {
  .upload-card {
    margin-bottom: 16px;
    border-radius: var(--radius-lg);

    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;

      .title {
        font-size: var(--font-size-md);
        font-weight: 600;
      }

      .tip-icon {
        color: var(--text-secondary);
        cursor: help;
      }
    }
  }

  .upload-area {
    border: 2px dashed var(--border-base);
    border-radius: var(--radius-lg);
    padding: 40px 20px;
    text-align: center;
    cursor: pointer;
    transition: all var(--transition-base);
    background: var(--bg-page);

    &:hover {
      border-color: var(--primary-color);
      background: var(--primary-light);
    }

    &.is-dragover {
      border-color: var(--primary-color);
      background: var(--primary-light);
      transform: scale(1.02);
    }

    &.has-image {
      padding: 20px;
    }

    .upload-placeholder {
      .upload-icon {
        color: var(--text-placeholder);
        margin-bottom: 16px;
      }

      .upload-text {
        font-size: var(--font-size-md);
        color: var(--text-regular);
        margin: 0 0 8px;
      }

      .upload-subtext {
        font-size: var(--font-size-sm);
        color: var(--text-secondary);
        margin: 0 0 16px;
      }
    }

    .preview-container {
      .preview-image {
        max-width: 100%;
        max-height: 400px;
        border-radius: var(--radius-base);
        margin-bottom: 16px;
        box-shadow: var(--shadow-base);
      }

      .preview-actions {
        display: flex;
        justify-content: center;
        gap: 12px;
      }
    }
  }

  .result-card {
    margin-bottom: 16px;
    border-radius: var(--radius-lg);

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .title {
        font-size: var(--font-size-md);
        font-weight: 600;
      }

      .header-actions {
        display: flex;
        align-items: center;
      }
    }

    .position-table {
      margin-bottom: 16px;

      .fund-name-cell {
        display: flex;
        align-items: center;
        gap: 8px;

        .unmatched {
          color: var(--text-secondary);
        }
      }

      .text-success {
        color: var(--success-color);
      }

      .text-danger {
        color: var(--danger-color);
      }

      .text-muted {
        color: var(--text-placeholder);
      }
    }

    .import-tips {
      margin-top: 16px;

      .tips-content {
        p {
          margin: 4px 0;
          font-size: 13px;
          color: var(--text-secondary);
        }
      }
    }
  }

  .raw-text-card {
    margin-bottom: 16px;
    border-radius: var(--radius-lg);

    .card-header {
      .title {
        font-size: var(--font-size-md);
        font-weight: 600;
      }
    }

    .raw-text-area {
      :deep(.el-textarea__inner) {
        font-family: monospace;
        font-size: 13px;
        background: var(--bg-page);
      }
    }
  }

  .help-card {
    border-radius: var(--radius-lg);

    .card-header {
      .title {
        font-size: var(--font-size-md);
        font-weight: 600;
      }
    }

    :deep(.el-steps--simple) {
      background: transparent;
      padding: 16px;
    }
  }
}
</style>
