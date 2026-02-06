<template>
  <div class="home-view">
    <!-- 统计卡片 - 新布局 -->
    <el-row :gutter="12" class="stats-row" v-if="fundStore.hasData">
      <!-- 第一个卡片：上涨/下跌数量 -->
      <el-col :xs="6" :sm="6" :lg="6">
        <div class="stat-card up-down">
          <div class="stat-icon">
            <el-icon size="18"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value up-down-value">
              <span class="text-success">{{ upCount }}</span>
              <span class="separator">/</span>
              <span class="text-danger">{{ downCount }}</span>
            </div>
            <div class="stat-label">上涨/下跌</div>
          </div>
        </div>
      </el-col>

      <!-- 第二个卡片：持仓总金额 -->
      <el-col :xs="6" :sm="6" :lg="6">
        <div class="stat-card portfolio-total">
          <div class="stat-icon">
            <el-icon size="18"><Wallet /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ formatCurrency(portfolioStore.totalValue) }}</div>
            <div class="stat-label">持仓金额</div>
          </div>
        </div>
      </el-col>

      <!-- 第三个卡片：单日实时总持仓涨跌幅 -->
      <el-col :xs="6" :sm="6" :lg="6">
        <div class="stat-card daily-change">
          <div class="stat-icon" :class="dailyChangePct >= 0 ? 'up' : 'down'">
            <el-icon size="18"><ArrowUp v-if="dailyChangePct >= 0" /><ArrowDown v-else /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value" :class="dailyChangePct >= 0 ? 'text-success' : 'text-danger'">
              {{ formatChange(dailyChangePct) }}
            </div>
            <div class="stat-label">今日涨跌</div>
          </div>
        </div>
      </el-col>

      <!-- 第四个卡片：单日实时涨跌金额 -->
      <el-col :xs="6" :sm="6" :lg="6">
        <div class="stat-card daily-amount">
          <div class="stat-icon" :class="dailyChangeAmount >= 0 ? 'up' : 'down'">
            <el-icon size="18"><Money /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value" :class="dailyChangeAmount >= 0 ? 'text-success' : 'text-danger'">
              {{ formatCurrency(dailyChangeAmount) }}
            </div>
            <div class="stat-label">今日盈亏</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 搜索和操作栏 -->
    <el-card class="search-card" shadow="never">
      <div class="search-bar">
        <el-select
          v-model="selectedSearchFund"
          filterable
          remote
          reserve-keyword
          placeholder="输入基金代码或名称搜索"
          :remote-method="handleSearch"
          :loading="searchLoading"
          class="search-input"
          style="flex: 1; max-width: 400px;"
          @change="onSearchFundSelect"
        >
          <el-option
            v-for="item in searchResults"
            :key="item.code"
            :label="`${item.code} - ${item.name}`"
            :value="item"
          />
        </el-select>
        <el-button :icon="Refresh" @click="refreshData" :loading="isRefreshing">{{ $t('home.refresh') }}</el-button>
        <el-button :icon="Download" @click="exportData">{{ $t('home.export') }}</el-button>
      </div>
    </el-card>

    <!-- 基金列表 -->
    <el-card class="fund-list-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">基金实时估值</span>
            <el-icon v-if="fundStore.loading" class="is-loading header-loading" size="16"><Loading /></el-icon>
            <el-tag v-if="fundStore.error && !fundStore.loading" type="danger" size="small" effect="light">
              {{ fundStore.error }}
            </el-tag>
          </div>
          <el-radio-group v-model="filterType" size="small">
              <el-radio-button value="all">全部</el-radio-button>
              <el-radio-button value="up">上涨</el-radio-button>
              <el-radio-button value="down">下跌</el-radio-button>
            </el-radio-group>
        </div>
      </template>

      <!-- 空状态 -->
      <el-empty v-if="!fundStore.hasData && !fundStore.loading" description="暂无数据">
        <template #description>
          <div class="empty-description">
            <p>暂无基金数据</p>
            <p class="sub-text">{{ fundStore.error || '点击下方按钮加载默认基金' }}</p>
          </div>
        </template>
        <el-button type="primary" @click="loadDefaultData">加载默认基金</el-button>
      </el-empty>

      <!-- 数据表格 -->
      <el-table
        v-else
        :data="filteredData"
        stripe
        style="width: 100%"
        height="calc(100vh - 320px)"
        :default-sort="{ prop: 'estimate_change', order: 'descending' }"
      >
        <el-table-column prop="code" label="基金代码" width="90" sortable />
        <el-table-column prop="name" label="基金名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="estimate_nav" label="估算净值" width="100" align="right">
          <template #default="{ row }">
            <span :class="getChangeClass(row.estimate_change)">
              {{ formatNav(row.estimate_nav) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="estimate_change" label="涨跌幅" width="95" align="right" sortable>
          <template #default="{ row }">
            <div class="change-cell" :class="getChangeClass(row.estimate_change)">
              <el-icon v-if="row.estimate_change > 0" size="12"><ArrowUp /></el-icon>
              <el-icon v-else-if="row.estimate_change < 0" size="12"><ArrowDown /></el-icon>
              <span>{{ formatChange(row.estimate_change) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="update_time" label="更新时间" width="140" />
        <el-table-column prop="status" label="状态" width="85">
          <template #default="{ row }">
            <el-tooltip placement="top">
              <template #content>
                <div style="font-size: 12px;">
                  <div>数据来源: {{ row.data_source || '未知' }}</div>
                  <div v-if="row.data_timestamp">更新时间: {{ formatDateTime(row.data_timestamp) }}</div>
                </div>
              </template>
              <el-tag :type="getStatusType(row.status)" size="small" effect="light" class="status-tag">
                {{ row.status }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-icons">
              <el-tooltip content="查看详情" placement="top">
                <el-button circle type="primary" size="small" @click="viewDetail(row)">
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              
              <el-tooltip 
                :content="isInPortfolio(row.code) ? '已在持仓中' : '加入持仓'" 
                placement="top"
              >
                <el-button 
                  circle 
                  :type="isInPortfolio(row.code) ? 'info' : 'success'"
                  size="small"
                  :disabled="isInPortfolio(row.code)"
                  @click="openAddDialog(row)"
                >
                  <el-icon><Plus v-if="!isInPortfolio(row.code)" /><Check v-else /></el-icon>
                </el-button>
              </el-tooltip>
              
              <el-tooltip content="取消关注" placement="top">
                <el-button circle type="danger" size="small" @click="removeFromWatchlist(row)">
                  <el-icon><Close /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 基金详情弹窗 -->
    <FundDetailDialog v-model="detailVisible" :fund="selectedFund" />

    <!-- 搜索结果对话框 -->
    <el-dialog
      v-model="searchResultDialogVisible"
      title="基金详情"
      width="400px"
      destroy-on-close
    >
      <div v-if="searchResultFund" class="search-result-content">
        <div class="fund-info">
          <h3>{{ searchResultFund.name }}</h3>
          <p class="fund-code">{{ searchResultFund.code }}</p>
        </div>
        <div class="fund-nav" v-if="searchResultFund.estimate_nav">
          <div class="nav-value" :class="getChangeClass(searchResultFund.estimate_change)">
            {{ formatNav(searchResultFund.estimate_nav) }}
          </div>
          <div class="nav-change" :class="getChangeClass(searchResultFund.estimate_change)">
            {{ formatChange(searchResultFund.estimate_change) }}
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="searchResultDialogVisible = false">关闭</el-button>
        <el-button type="success" @click="addSearchFundToWatchlist">
          添加关注
        </el-button>
        <el-button type="primary" @click="addSearchFundToPortfolio">
          添加持仓
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加持仓对话框 -->
    <el-dialog
      v-model="addDialogVisible"
      title="添加持仓"
      width="400px"
      destroy-on-close
    >
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="基金代码">
          <el-input v-model="addForm.fund_code" disabled />
        </el-form-item>
        <el-form-item label="基金名称">
          <el-input v-model="addForm.fund_name" disabled />
        </el-form-item>
        <el-form-item label="持有份额">
          <el-input-number
            v-model="addForm.hold_shares"
            :min="0"
            :precision="2"
            :step="100"
            style="width: 100%"
            placeholder="请输入持有份额"
          />
        </el-form-item>
        <el-form-item label="成本价">
          <el-input-number
            v-model="addForm.cost_nav"
            :min="0"
            :precision="4"
            :step="0.0001"
            style="width: 100%"
            placeholder="请输入成本价"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAddToPortfolio" :loading="isAdding">
          确认添加
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'HomeView'
})

import { ref, computed, onMounted, reactive } from 'vue'
import { ArrowUp, ArrowDown, Search, Refresh, Wallet, TrendCharts, Loading, Download, Money, View, Plus, Check, Close } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { useFundStore } from '@/stores/fundStore'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { dataManager } from '@/stores/dataManager'
import { ElMessage } from 'element-plus'
import FundDetailDialog from '@/components/FundDetail/FundDetailDialog.vue'
import { exportFundsToCSV } from '@/utils/export'
import fundApi, { type FundRealtimeData } from '@/api/fund'

const { t } = useI18n()
const fundStore = useFundStore()
const portfolioStore = usePortfolioStore()
const isRefreshing = ref(false)

// 搜索和筛选
const searchKeyword = ref('')
const filterType = ref<'all' | 'up' | 'down'>('all')
const detailVisible = ref(false)
const selectedFund = ref<FundRealtimeData | null>(null)

// 搜索相关
const searchLoading = ref(false)
const searchResults = ref<FundSearchItem[]>([])
const selectedSearchFund = ref<FundSearchItem | null>(null)

// 添加持仓对话框状态
const addDialogVisible = ref(false)
const isAdding = ref(false)
const currentAddFund = ref<FundRealtimeData | null>(null)
const addForm = reactive({
  fund_code: '',
  fund_name: '',
  hold_shares: 100,
  cost_nav: 0
})

// 搜索基金对话框
const searchResultDialogVisible = ref(false)
const searchResultFund = ref<FundRealtimeData | null>(null)

// 统计数据
const upCount = computed(() => fundStore.upFunds.length)
const downCount = computed(() => fundStore.downFunds.length)

// 计算单日实时总持仓涨跌幅和涨跌金额
const dailyChangePct = computed(() => {
  if (portfolioStore.items.length === 0) return 0
  // 计算今日总涨跌金额
  let totalDailyChange = 0
  let totalValue = 0
  
  portfolioStore.items.forEach(item => {
    const currentNav = item.current_nav || item.cost_nav || 0
    const holdShares = item.hold_shares || 0
    const currentValue = currentNav * holdShares
    const currentChange = item.current_change || 0 // 今日涨跌幅百分比
    
    // 该基金的今日涨跌金额 = 当前市值 * 今日涨跌幅 / 100
    const dailyChangeAmount = currentValue * (currentChange / 100)
    totalDailyChange += dailyChangeAmount
    totalValue += currentValue
  })
  
  // 今日总涨跌幅百分比
  return totalValue > 0 ? (totalDailyChange / totalValue) * 100 : 0
})

const dailyChangeAmount = computed(() => {
  if (portfolioStore.items.length === 0) return 0
  // 计算今日总涨跌金额
  let totalDailyChange = 0
  
  portfolioStore.items.forEach(item => {
    const currentNav = item.current_nav || item.cost_nav || 0
    const holdShares = item.hold_shares || 0
    const currentValue = currentNav * holdShares
    const currentChange = item.current_change || 0 // 今日涨跌幅百分比
    
    // 该基金的今日涨跌金额 = 当前市值 * 今日涨跌幅 / 100
    const dailyChangeAmount = currentValue * (currentChange / 100)
    totalDailyChange += dailyChangeAmount
  })
  
  return totalDailyChange
})

// 筛选后的数据
const filteredData = computed(() => {
  let data = fundStore.realtimeData
  
  // 搜索筛选
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    data = data.filter(f => 
      f.code.toLowerCase().includes(keyword) || 
      f.name.toLowerCase().includes(keyword)
    )
  }
  
  // 类型筛选
  if (filterType.value === 'up') {
    data = data.filter(f => (f.estimate_change || 0) > 0)
  } else if (filterType.value === 'down') {
    data = data.filter(f => (f.estimate_change || 0) < 0)
  }
  
  return data
})

// 格式化净值
const formatNav = (val: string | number | null) => {
  if (val === null || val === undefined || val === '') return '--'
  const num = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(num)) return '--'
  return num.toFixed(4)
}

// 格式化涨跌幅
const formatChange = (val: number | string | null) => {
  if (val === null || val === undefined) return '--'
  const num = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(num)) return '--'
  return (num > 0 ? '+' : '') + num.toFixed(2) + '%'
}

// 格式化金额 - 显示两位小数
const formatCurrency = (val: number): string => {
  if (val === null || val === undefined || isNaN(val)) return '--'
  return '¥' + val.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 获取涨跌样式
const getChangeClass = (val: number | null) => {
  if (val === null || val === undefined) return ''
  if (val > 0) return 'text-success'
  if (val < 0) return 'text-danger'
  return ''
}

// 获取状态标签类型
const getStatusType = (status: string): 'success' | 'info' | 'warning' | 'danger' => {
  if (status === '正常') return 'success'
  if (status === '最新净值') return 'info'
  if (status === '场内行情') return 'warning'
  return 'info'
}

// 格式化日期时间
const formatDateTime = (timestamp: string): string => {
  if (!timestamp) return '--'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return timestamp
  }
}

// 搜索基金
const handleSearch = async (query: string) => {
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

// 选择搜索结果
const onSearchFundSelect = async (fund: FundSearchItem) => {
  if (!fund) return

  try {
    // 获取基金实时数据
    const fundData = await fundApi.getRealtime(fund.code)
    searchResultFund.value = fundData
    searchResultDialogVisible.value = true
  } catch (e) {
    console.error('获取基金详情失败:', e)
    ElMessage.error('获取基金详情失败')
  }
}

// 添加搜索到的基金到关注列表
const addSearchFundToWatchlist = async () => {
  if (!searchResultFund.value) return

  try {
    const exists = fundStore.fundList.includes(searchResultFund.value.code)
    if (exists) {
      ElMessage.warning('该基金已在关注列表中')
      return
    }

    fundStore.addFund(searchResultFund.value.code)
    await fundStore.fetchRealtimeData()
    ElMessage.success(`已添加 ${searchResultFund.value.name} 到关注列表`)
    searchResultDialogVisible.value = false
    selectedSearchFund.value = null
  } catch (e) {
    console.error('添加失败:', e)
    ElMessage.error('添加失败')
  }
}

// 添加搜索到的基金到持仓
const addSearchFundToPortfolio = async () => {
  if (!searchResultFund.value) return

  // 检查是否已在持仓中
  const exists = portfolioStore.items.some(item => item.fund_code === searchResultFund.value!.code)
  if (exists) {
    ElMessage.warning('该基金已在持仓列表中')
    return
  }

  // 打开添加持仓对话框
  currentAddFund.value = searchResultFund.value
  addForm.fund_code = searchResultFund.value.code
  addForm.fund_name = searchResultFund.value.name
  addForm.hold_shares = 100
  const nav = typeof searchResultFund.value.estimate_nav === 'string'
    ? parseFloat(searchResultFund.value.estimate_nav)
    : searchResultFund.value.estimate_nav
  addForm.cost_nav = nav || 0

  searchResultDialogVisible.value = false
  selectedSearchFund.value = null
  addDialogVisible.value = true
}

// 刷新数据
const refreshData = async () => {
  isRefreshing.value = true
  await dataManager.refreshAll()
  isRefreshing.value = false
}

// 加载默认数据
const loadDefaultData = () => {
  fundStore.resetToDefault()
}

// 查看基金详情
const viewDetail = (fund: FundRealtimeData) => {
  selectedFund.value = fund
  detailVisible.value = true
}

// 导出数据
const exportData = () => {
  const data = fundStore.realtimeData
  if (data.length === 0) {
    ElMessage.warning(t('home.noDataToExport'))
    return
  }
  exportFundsToCSV(data)
  ElMessage.success(t('home.exportSuccess'))
}

// 检查基金是否已在持仓中
const isInPortfolio = (code: string): boolean => {
  return portfolioStore.items.some(item => item.fund_code === code)
}

// 从关注列表移除基金
const removeFromWatchlist = async (fund: FundRealtimeData) => {
  try {
    await ElMessageBox.confirm(
      `确定要从关注列表移除 ${fund.name} (${fund.code}) 吗？`,
      '确认移除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    fundStore.removeFund(fund.code)
    ElMessage.success(`已移除 ${fund.name}`)
  } catch {
    // 用户取消
  }
}

// 打开添加持仓对话框
const openAddDialog = (fund: FundRealtimeData) => {
  if (isInPortfolio(fund.code)) {
    ElMessage.warning('该基金已在持仓列表中')
    return
  }
  currentAddFund.value = fund
  addForm.fund_code = fund.code
  addForm.fund_name = fund.name
  addForm.hold_shares = 100
  // 默认成本价为当前估算净值
  const nav = typeof fund.estimate_nav === 'string' ? parseFloat(fund.estimate_nav) : fund.estimate_nav
  addForm.cost_nav = nav || 0
  addDialogVisible.value = true
}

// 确认添加到持仓
const confirmAddToPortfolio = async () => {
  if (!currentAddFund.value) return

  if (addForm.hold_shares <= 0) {
    ElMessage.warning('请输入有效的持有份额')
    return
  }

  if (addForm.cost_nav <= 0) {
    ElMessage.warning('请输入有效的成本价')
    return
  }

  isAdding.value = true
  try {
    const costAmount = addForm.cost_nav * addForm.hold_shares
    const success = await portfolioStore.addItem({
      fund_code: addForm.fund_code,
      fund_name: addForm.fund_name,
      hold_shares: addForm.hold_shares,
      cost_amount: costAmount,
      cost_nav: addForm.cost_nav
    })

    if (success) {
      ElMessage.success(t('portfolio.addSuccess', { name: addForm.fund_name }))
      addDialogVisible.value = false
    } else {
      ElMessage.error(t('portfolio.addFailed'))
    }
  } catch {
    ElMessage.error(t('portfolio.addFailed'))
  } finally {
    isAdding.value = false
  }
}

onMounted(() => {
  // 数据已由 MainLayout.vue 中的 dataManager.initialize() 统一加载
  // 这里不需要重复加载
  console.log('[HomeView] 页面已挂载，数据由 DataManager 统一管理')
})
</script>

<style scoped lang="scss">
.home-view {
  .stats-row {
    margin-bottom: 12px;
  }
  
  .stat-card {
    background: var(--bg-card);
    border-radius: var(--radius-base);
    padding: 12px 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    box-shadow: var(--shadow-base);
    border: 1px solid var(--border-light);
    transition: all var(--transition-base);
    
    &:hover {
      transform: translateY(-1px);
      box-shadow: var(--shadow-md);
    }
    
    .stat-icon {
      width: 32px;
      height: 32px;
      border-radius: var(--radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      background: var(--info-light);
      color: var(--primary-color);

      &.up {
        background: var(--success-light);
        color: var(--success-color);
      }

      &.down {
        background: var(--danger-light);
        color: var(--danger-color);
      }
    }

    &.up-down .stat-icon {
      background: linear-gradient(135deg, var(--success-light) 50%, var(--danger-light) 50%);
      color: var(--primary-color);
    }

    &.portfolio-total .stat-icon {
      background: var(--info-light);
      color: var(--primary-color);
    }

    &.daily-change .stat-icon {
      background: var(--warning-light);
      color: var(--warning-color);
    }

    &.daily-amount .stat-icon {
      background: var(--warning-light);
      color: var(--warning-color);
    }
    
    .stat-info {
      text-align: center;

      .stat-value {
        font-size: 18px;
        font-weight: 700;
        line-height: 1.2;

        &.up-down-value {
          display: flex;
          align-items: center;
          gap: 4px;

          .separator {
            color: var(--text-secondary);
            font-weight: 400;
          }
        }
      }

      .stat-label {
        font-size: 12px;
        color: var(--text-secondary);
        margin-top: 2px;
      }
    }
  }
  
  .search-card {
    margin-bottom: 12px;
    border-radius: var(--radius-lg);
    
    :deep(.el-card__body) {
      padding: 12px 16px;
    }
    
    .search-bar {
      display: flex;
      gap: 8px;
      
      .search-input {
        flex: 1;
        max-width: 300px;
      }
    }
  }
  
  .fund-list-card {
    border-radius: var(--radius-lg);
    
    :deep(.el-card__header) {
      padding: 12px 16px;
    }
    
    :deep(.el-card__body) {
      padding: 0;
    }
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .header-left {
        display: flex;
        align-items: center;
        gap: 8px;
        
        .title {
          font-size: var(--font-size-md);
          font-weight: 600;
        }
        
        .header-loading {
          color: var(--primary-color);
        }
      }
    }
    
    .change-cell {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 2px;
      font-weight: 600;
      font-size: 13px;
    }
    
    .action-icons {
      display: flex;
      justify-content: center;
      gap: 4px;
      
      .el-button {
        padding: 4px;
        
        .el-icon {
          font-size: 14px;
        }
      }
    }
    
    .empty-description {
      text-align: center;
      
      p {
        margin: 0;
        color: var(--text-regular);
        
        &.sub-text {
          font-size: var(--font-size-sm);
          color: var(--text-secondary);
          margin-top: 8px;
        }
      }
    }
    
    :deep(.el-table) {
      .el-table__cell {
        padding: 8px 0;
      }
      
      .el-tag {
        padding: 0 6px;
        height: 20px;
        line-height: 18px;
        font-size: 11px;
      }
    }
  }
}

.text-success {
  color: var(--success-color);
}

.text-danger {
  color: var(--danger-color);
}

.search-result-content {
  .fund-info {
    text-align: center;
    margin-bottom: 20px;

    h3 {
      margin: 0 0 8px;
      font-size: 18px;
      color: var(--text-primary);
    }

    .fund-code {
      margin: 0;
      font-size: 14px;
      color: var(--text-secondary);
      font-family: monospace;
    }
  }

  .fund-nav {
    text-align: center;
    padding: 20px;
    background: var(--bg-page);
    border-radius: var(--radius-base);

    .nav-value {
      font-size: 32px;
      font-weight: 700;
      margin-bottom: 8px;
    }

    .nav-change {
      font-size: 16px;
    }
  }
}
</style>
