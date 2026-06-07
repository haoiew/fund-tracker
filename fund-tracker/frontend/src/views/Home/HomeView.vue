<template>
  <div class="home-view page-shell">
    <section class="page-toolbar">
      <div class="page-toolbar__main">
        <span class="page-toolbar__icon">
          <el-icon><DataLine /></el-icon>
        </span>
        <div class="page-toolbar__copy">
          <h2 class="page-toolbar__title">基金实时总览</h2>
          <p class="page-toolbar__meta">关注 {{ fundStore.realtimeData.length }} 只 · 持仓 {{ portfolioStore.itemCount }} 条 · 今日 {{ formatChange(dailyChangePct) }}</p>
        </div>
      </div>
      <div class="page-toolbar__actions">
        <el-button :icon="Refresh" @click="refreshData" :loading="isRefreshing">
          {{ $t('home.refresh') }}
        </el-button>
        <el-button :icon="Download" @click="exportData">
          {{ $t('home.export') }}
        </el-button>
        <el-button
          v-if="!fundStore.hasData"
          type="primary"
          :icon="Wallet"
          @click="loadDefaultData"
          :loading="isLoadingDefault"
        >
          {{ $t('home.loadDefault') }}
        </el-button>
      </div>
    </section>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row" v-if="fundStore.hasData">
      <!-- 第一个卡片：上涨/下跌数量 -->
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card up-down">
          <div class="stat-icon" :class="upCount >= downCount ? 'up' : 'down'">
            <el-icon size="20"><TrendChartsIcon /></el-icon>
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
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card portfolio-total">
          <div class="stat-icon primary">
            <el-icon size="20"><Wallet /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ formatCurrency(portfolioStore.totalValue) }}</div>
            <div class="stat-label">持仓金额</div>
          </div>
        </div>
      </el-col>

      <!-- 第三个卡片：单日实时总持仓涨跌幅 -->
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card daily-change">
          <div class="stat-icon" :class="dailyChangePct >= 0 ? 'up' : 'down'">
            <el-icon size="20"><DataLine /></el-icon>
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
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card daily-amount">
          <div class="stat-icon" :class="dailyChangeAmount >= 0 ? 'up' : 'down'">
            <el-icon size="20"><Coin /></el-icon>
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
    <section class="search-card surface-panel">
      <div class="toolbar-row search-toolbar">
        <div class="search-box">
          <el-input
            v-model="searchInputValue"
            placeholder="输入基金代码或名称搜索"
            class="search-input"
            :prefix-icon="Search"
            clearable
            @input="onSearchInput"
            @focus="onSearchFocus"
            @keydown.esc="closeSearchResults"
          />
          <div v-if="showSearchResults" class="search-results-dropdown" v-click-outside="onClickOutsideSearch">
            <div v-if="searchLoading" class="search-loading">
              <el-icon class="is-loading" size="16"><Loading /></el-icon>
              <span>搜索中...</span>
            </div>
            <div v-else-if="searchResults.length === 0 && searchInputValue.length >= 2" class="search-empty">
              <el-icon size="16"><InfoFilled /></el-icon>
              <span>未找到相关基金</span>
            </div>
            <div v-else-if="searchInputValue.length < 2" class="search-hint">
              <el-icon size="16"><InfoFilled /></el-icon>
              <span>请输入至少2个字符</span>
            </div>
            <div v-else class="search-results-list">
              <div
                v-for="item in searchResults"
                :key="item.code"
                class="search-result-item"
                @click="onSearchFundSelect(item)"
              >
                <span class="fund-code">{{ item.code }}</span>
                <span class="fund-name">{{ item.name }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 基金列表 -->
    <section class="fund-list-card surface-panel">
      <div class="card-header">
        <div class="header-left">
          <span class="title">基金实时估值</span>
          <el-icon v-if="fundStore.loading" class="is-loading header-loading" size="16"><Loading /></el-icon>
          <el-tag v-if="fundStore.error && !fundStore.loading" type="danger" size="small" effect="light">
            {{ fundStore.error }}
          </el-tag>
          <template v-if="selectedFunds.length > 0">
            <el-tag type="primary" size="small" effect="dark">
              已选 {{ selectedFunds.length }} 只
            </el-tag>
            <el-button type="danger" size="small" :icon="Delete" @click="batchRemoveFromWatchlist">
              批量移除
            </el-button>
            <el-button size="small" @click="clearSelection">取消选择</el-button>
          </template>
        </div>
        <el-radio-group v-model="filterType" size="small">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="up">上涨</el-radio-button>
          <el-radio-button value="down">下跌</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 空状态 -->
      <el-empty v-if="!fundStore.hasData && !fundStore.loading" description="暂无数据">
        <template #description>
          <div class="empty-description">
            <p>暂无基金数据</p>
            <p class="sub-text">{{ fundStore.error || '点击下方按钮加载默认基金' }}</p>
          </div>
        </template>
        <el-button type="primary" @click="loadDefaultData" :loading="isLoadingDefault">加载默认基金</el-button>
      </el-empty>

      <!-- 数据表格 -->
      <el-table
        v-else
        ref="tableRef"
        :data="filteredData"
        row-key="code"
        class="fund-table"
        style="width: 100%"
        :expand-row-keys="expandedRowKeys"
        :default-sort="{ prop: 'estimate_change', order: 'descending' }"
        :row-class-name="getTableRowClassName"
        @selection-change="handleSelectionChange"
        @expand-change="handleExpandChange"
      >
        <el-table-column type="selection" width="40" />
        <el-table-column type="expand" width="36">
          <template #default="{ row }">
            <div class="fund-expanded-panel">
              <div class="fund-expanded-summary">
                <div class="expanded-title-row">
                  <div>
                    <span class="expanded-kicker">FUND DETAIL</span>
                    <h3>{{ row.name }}</h3>
                  </div>
                  <el-button text size="small" @click="collapseFundDetail">收起</el-button>
                </div>

                <div class="expanded-metrics">
                  <div class="expanded-metric">
                    <span>估算净值</span>
                    <strong :class="getChangeClass(row.estimate_change)">{{ formatNav(row.estimate_nav) }}</strong>
                  </div>
                  <div class="expanded-metric">
                    <span>实时涨跌</span>
                    <strong :class="getChangeClass(row.estimate_change)">{{ formatChange(row.estimate_change) }}</strong>
                  </div>
                  <div class="expanded-metric">
                    <span>上一净值</span>
                    <strong>{{ formatNav(row.previous_nav ?? null) }}</strong>
                  </div>
                  <div class="expanded-metric">
                    <span>累计净值</span>
                    <strong>{{ formatNav(row.accumulated_nav ?? null) }}</strong>
                  </div>
                </div>

                <div class="expanded-meta-grid">
                  <div>
                    <span>基金代码</span>
                    <strong>{{ row.code }}</strong>
                  </div>
                  <div>
                    <span>数据来源</span>
                    <strong>{{ row.data_source || '自动选择' }}</strong>
                  </div>
                  <div>
                    <span>更新时间</span>
                    <strong>{{ row.data_timestamp ? formatDateTime(row.data_timestamp) : row.update_time || '--' }}</strong>
                  </div>
                  <div>
                    <span>状态</span>
                    <strong>{{ row.status || '--' }}</strong>
                  </div>
                </div>
              </div>

              <div class="fund-expanded-chart">
                <FundChart :code="row.code" :name="row.name" default-range="1M" embedded :height="292" />
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="code" label="基金" min-width="240" sortable>
          <template #default="{ row }">
            <div class="fund-identity">
              <span class="fund-code-pill">{{ row.code }}</span>
              <span class="fund-name-text">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="estimate_nav" label="估算净值" width="116" align="right">
          <template #default="{ row }">
            <div class="nav-cell" :class="getChangeClass(row.estimate_change)">
              {{ formatNav(row.estimate_nav) }}
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="estimate_change" label="涨跌幅" width="112" align="right" sortable>
          <template #default="{ row }">
            <div class="change-pill" :class="getChangeTone(row.estimate_change)">
              <el-icon v-if="row.estimate_change > 0" size="12"><ArrowUp /></el-icon>
              <el-icon v-else-if="row.estimate_change < 0" size="12"><ArrowDown /></el-icon>
              <span>{{ formatChange(row.estimate_change) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="update_time" label="更新时间" width="154">
          <template #default="{ row }">
            <div class="time-cell">
              <span>{{ row.update_time || '--' }}</span>
              <small>{{ row.data_source || 'auto' }}</small>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="104" align="center">
          <template #default="{ row }">
            <el-tooltip placement="top">
              <template #content>
                <div style="font-size: 12px;">
                  <div>数据来源: {{ row.data_source || '未知' }}</div>
                  <div v-if="row.data_timestamp">更新时间: {{ formatDateTime(row.data_timestamp) }}</div>
                  <div style="color: #409eff; margin-top: 4px;">点击切换数据源</div>
                </div>
              </template>
              <el-tag 
                :type="getStatusType(row.status)" 
                size="small" 
                effect="light" 
                class="status-tag"
                @click.stop="showDataSourceMenu(row)"
              >
                <span class="status-dot-inline"></span>
                {{ row.status }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="110" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-icons">
              <el-tooltip :content="isFundExpanded(row) ? '收起详情' : '展开详情'" placement="top">
                <el-button circle :type="isFundExpanded(row) ? 'primary' : 'default'" size="small" @click="toggleFundDetail(row)">
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
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

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

    <!-- 数据源对比弹窗 -->
    <el-dialog
      v-model="dataSourceDialogVisible"
      title="数据源对比"
      width="700px"
      destroy-on-close
    >
      <div v-if="dataSourceLoading" class="loading-container">
        <el-icon class="is-loading" size="32"><Loading /></el-icon>
        <p>正在加载数据源...</p>
      </div>
      <div v-else-if="dataSourceData" class="data-source-content">
        <div class="fund-header">
          <h3>{{ dataSourceData.name }}</h3>
          <span class="fund-code">{{ dataSourceData.code }}</span>
        </div>
        <el-table :data="dataSourceData.sources" style="width: 100%" border>
          <el-table-column prop="source" label="数据源" width="120" />
          <el-table-column prop="estimate_nav" label="估算净值" width="100">
            <template #default="{ row }">
              <span :class="getChangeClass(row.estimate_change_pct)">
                {{ row.estimate_nav?.toFixed(4) || '--' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="estimate_change_pct" label="涨跌幅" width="100">
            <template #default="{ row }">
              <span :class="getChangeClass(row.estimate_change_pct)">
                {{ formatChange(row.estimate_change_pct) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="update_time" label="更新时间" width="140" />
          <el-table-column prop="is_fresh" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_fresh ? 'success' : 'warning'" size="small">
                {{ row.is_fresh ? '正常' : '过期' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center">
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                :disabled="row.source === dataSourceData.best_source"
                @click="selectDataSource(row.source)"
              >
                {{ row.source === dataSourceData.best_source ? '当前' : '选择' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="data-source-tips">
          <el-alert
            title="提示"
            type="info"
            :closable="false"
            show-icon
          >
            <template #default>
              当前最佳数据源: <strong>{{ dataSourceData.best_source || '自动选择' }}</strong>，
              共获取到 <strong>{{ dataSourceData.total_sources }}</strong> 个数据源
            </template>
          </el-alert>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'HomeView'
})

import { ref, computed, onMounted, reactive } from 'vue'
import { ArrowUp, ArrowDown, Search, Refresh, Wallet, Loading, Download, View, Plus, Check, DataLine, Coin, TrendCharts as TrendChartsIcon, InfoFilled, Delete } from '@element-plus/icons-vue'
import { ClickOutside as vClickOutside } from 'element-plus'
import type { TableInstance } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { useFundStore } from '@/stores/fundStore'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { dataManager } from '@/stores/dataManager'
import { ElMessage, ElMessageBox } from 'element-plus'
import FundChart from '@/components/Charts/FundChart.vue'
import { exportFundsToCSV } from '@/utils/export'
import fundApi, { type FundRealtimeData, type FundSearchItem } from '@/api/fund'

const { t } = useI18n()
const fundStore = useFundStore()
const portfolioStore = usePortfolioStore()
const isRefreshing = ref(false)
const isLoadingDefault = ref(false)
const selectedFunds = ref<FundRealtimeData[]>([])
const tableRef = ref<TableInstance>()
const expandedRowKeys = ref<string[]>([])

// 搜索和筛选
const searchKeyword = ref('')
const filterType = ref<'all' | 'up' | 'down'>('all')

// 搜索相关
const searchInputValue = ref('')
const searchLoading = ref(false)
const searchResults = ref<FundSearchItem[]>([])
const selectedSearchFund = ref<FundSearchItem | null>(null)
const showSearchResults = ref(false)
const searchDebounceTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const isSearchInProgress = ref(false)

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

// 数据源对比弹窗
const dataSourceDialogVisible = ref(false)
const dataSourceLoading = ref(false)

interface DataSourceComparisonItem {
  source: string
  priority: number
  estimate_nav: number | null
  estimate_change_pct: number | null
  last_nav: number | null
  last_change_pct: number | null
  update_time: string
  is_fresh: boolean
}

const dataSourceData = ref<{
  code: string
  name: string
  sources: DataSourceComparisonItem[]
  best_source: string | null
  total_sources: number
} | null>(null)
const currentDataSourceFund = ref<FundRealtimeData | null>(null)

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

const getChangeTone = (val: number | string | null) => {
  if (val === null || val === undefined) return 'is-flat'
  const num = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(num) || num === 0) return 'is-flat'
  return num > 0 ? 'is-up' : 'is-down'
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

// 防抖搜索处理
const onSearchInput = () => {
  // 清除之前的定时器
  if (searchDebounceTimer.value) {
    clearTimeout(searchDebounceTimer.value)
  }

  // 显示搜索结果面板
  showSearchResults.value = true

  const query = searchInputValue.value.trim()

  // 如果输入为空，清空结果
  if (!query) {
    searchResults.value = []
    searchLoading.value = false
    return
  }

  // 如果输入长度小于2，不执行搜索但保持面板打开
  if (query.length < 2) {
    searchResults.value = []
    return
  }

  // 设置加载状态
  searchLoading.value = true

  // 防抖处理：300ms后执行搜索
  searchDebounceTimer.value = setTimeout(async () => {
    await executeSearch(query)
  }, 300)
}

// 执行搜索
const executeSearch = async (query: string) => {
  // 如果已有搜索在进行中，等待完成
  if (isSearchInProgress.value) {
    return
  }

  isSearchInProgress.value = true

  try {
    const results = await fundApi.search(query, 20)
    // 只有当搜索结果面板仍然显示时才更新结果
    if (showSearchResults.value) {
      searchResults.value = results
    }
  } catch (e) {
    console.error('搜索基金失败:', e)
    if (showSearchResults.value) {
      searchResults.value = []
    }
  } finally {
    searchLoading.value = false
    isSearchInProgress.value = false
  }
}

// 搜索框获得焦点
const onSearchFocus = () => {
  showSearchResults.value = true
}

// 关闭搜索结果
const closeSearchResults = () => {
  showSearchResults.value = false
}

// 点击搜索结果外部
const onClickOutsideSearch = () => {
  // 只有在搜索未进行时才允许关闭
  if (!isSearchInProgress.value && !searchLoading.value) {
    showSearchResults.value = false
  }
}

// 选择搜索结果
const onSearchFundSelect = async (fund: FundSearchItem) => {
  if (!fund) return

  // 清空搜索输入和关闭结果面板
  searchInputValue.value = ''
  searchResults.value = []
  showSearchResults.value = false

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
  try {
    await dataManager.refreshAll()
    ElMessage.success('数据已更新')
  } catch {
    ElMessage.error('刷新失败，请检查后端服务是否运行')
  } finally {
    isRefreshing.value = false
  }
}

// 加载默认数据
const loadDefaultData = async () => {
  isLoadingDefault.value = true
  try {
    console.log('[HomeView] 加载默认基金...')
    await fundStore.resetToDefault()
    console.log('[HomeView] 默认基金加载完成')
  } catch (e) {
    console.error('[HomeView] 加载默认基金失败:', e)
    ElMessage.error('加载默认基金失败，请检查后端服务是否运行')
  } finally {
    isLoadingDefault.value = false
  }
}

const isFundExpanded = (fund: FundRealtimeData) => expandedRowKeys.value.includes(fund.code)

const toggleFundDetail = (fund: FundRealtimeData) => {
  expandedRowKeys.value = isFundExpanded(fund) ? [] : [fund.code]
}

const collapseFundDetail = () => {
  expandedRowKeys.value = []
}

const handleExpandChange = (row: FundRealtimeData, expandedRows: FundRealtimeData[]) => {
  const isExpanded = expandedRows.some(item => item.code === row.code)
  expandedRowKeys.value = isExpanded ? [row.code] : []
}

const getTableRowClassName = ({ row }: { row: FundRealtimeData }) => {
  return isFundExpanded(row) ? 'is-expanded-row' : ''
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

// 批量删除选中基金
const batchRemoveFromWatchlist = async () => {
  if (selectedFunds.value.length === 0) {
    ElMessage.warning('请先选择要移除的基金')
    return
  }

  const names = selectedFunds.value.map(f => `${f.name}(${f.code})`).join('、')
  try {
    await ElMessageBox.confirm(
      `确定要从关注列表移除以下 ${selectedFunds.value.length} 只基金吗？\n${names}`,
      '批量移除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const codes = selectedFunds.value.map(f => f.code)
    dataManager.removeFunds(codes)
    selectedFunds.value = []
    ElMessage.success(`已批量移除 ${codes.length} 只基金`)
  } catch {
    // 用户取消
  }
}

// 处理选择变化
const handleSelectionChange = (selection: FundRealtimeData[]) => {
  selectedFunds.value = selection
}

// 清空选择
const clearSelection = () => {
  selectedFunds.value = []
  tableRef.value?.clearSelection()
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

// 选择数据源
const selectDataSource = async (source: string) => {
  if (!currentDataSourceFund.value) return
  
  ElMessage.success(`已选择 ${source} 作为数据源`)
  dataSourceDialogVisible.value = false
  
  // 刷新该基金数据
  await refreshData()
}

// 显示数据源菜单
const showDataSourceMenu = async (fund: FundRealtimeData) => {
  console.log('点击状态标签，基金:', fund.code, fund.name)
  currentDataSourceFund.value = fund
  
  // 直接打开数据源对比弹窗
  dataSourceDialogVisible.value = true
  dataSourceLoading.value = true
  
  try {
    console.log('正在获取数据源对比...')
    const result = await fundApi.getDataSources(fund.code, fund.name)
    console.log('数据源对比结果:', result)
    dataSourceData.value = result
  } catch (error) {
    console.error('获取数据源对比失败:', error)
    ElMessage.error('获取数据源对比失败')
  } finally {
    dataSourceLoading.value = false
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
  display: flex;
  flex-direction: column;
  gap: 14px;

  .stats-row {
    margin-bottom: 0;
  }

  .stat-card {
    min-height: 88px;
    background: var(--bg-card);
    border-radius: var(--radius-base);
    padding: 14px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: var(--shadow-light);
    border: 1px solid var(--border-light);
    transition: transform var(--transition-base), box-shadow var(--transition-base), border-color var(--transition-base);

    &:hover {
      transform: translateY(-1px);
      box-shadow: var(--shadow-base);
      border-color: rgba(37, 99, 235, 0.18);
    }

    .stat-icon {
      width: 38px;
      height: 38px;
      border-radius: var(--radius-base);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      background: rgba(37, 99, 235, 0.08);
      color: var(--primary-color);
      transition: all var(--transition-base);

      &.up {
        background: linear-gradient(135deg, rgba(20, 184, 166, 0.96) 0%, rgba(16, 185, 129, 0.96) 100%);
        color: white;
        box-shadow: 0 8px 18px rgba(20, 184, 166, 0.18);
      }

      &.down {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.96) 0%, rgba(248, 113, 113, 0.96) 100%);
        color: white;
        box-shadow: 0 8px 18px rgba(239, 68, 68, 0.18);
      }

      &.primary {
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.96) 0%, rgba(79, 131, 255, 0.96) 100%);
        color: white;
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18);
      }
    }

    &.up-down .stat-icon {
      background: linear-gradient(135deg, rgba(20, 184, 166, 0.96) 0%, rgba(37, 99, 235, 0.96) 50%, rgba(239, 68, 68, 0.96) 100%);
      color: white;
    }

    &.portfolio-total .stat-icon {
      background: linear-gradient(135deg, rgba(37, 99, 235, 0.96) 0%, rgba(79, 131, 255, 0.96) 100%);
      color: white;
    }

    &.daily-change .stat-icon {
      background: linear-gradient(135deg, rgba(245, 158, 11, 0.96) 0%, rgba(251, 191, 36, 0.96) 100%);
      color: white;
    }

    &.daily-amount .stat-icon {
      background: linear-gradient(135deg, rgba(139, 92, 246, 0.96) 0%, rgba(124, 58, 237, 0.96) 100%);
      color: white;
    }

    .stat-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
      text-align: left;
      min-width: 0;

      .stat-value {
        font-size: 20px;
        font-weight: 800;
        line-height: 1.15;

        &.up-down-value {
          display: flex;
          align-items: center;
          gap: 4px;

          .separator {
            color: var(--text-secondary);
            font-weight: 500;
          }
        }
      }

      .stat-label {
        font-size: 12px;
        color: var(--text-secondary);
      }
    }
  }

  .search-card {
    padding: 14px 16px;
  }

  .search-toolbar {
    gap: 12px;
  }

  .search-box {
    position: relative;
    flex: 1;
    min-width: 280px;
    max-width: 560px;

    .search-input {
      width: 100%;
    }

    .search-results-dropdown {
      position: absolute;
      top: calc(100% + 6px);
      left: 0;
      right: 0;
      z-index: 100;
      max-height: 320px;
      overflow-y: auto;
      background: var(--bg-card);
      border: 1px solid var(--border-light);
      border-radius: var(--radius-base);
      box-shadow: var(--shadow-lg);
      backdrop-filter: blur(14px);

      .search-loading,
      .search-empty,
      .search-hint {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 16px;
        color: var(--text-secondary);
        font-size: 14px;
      }

      .search-results-list {
        padding: 6px 0;

        .search-result-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 11px 16px;
          cursor: pointer;
          transition: background-color var(--transition-fast);

          &:hover {
            background: var(--bg-hover);
          }

          .fund-code {
            min-width: 72px;
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--primary-color);
            font-weight: 700;
          }

          .fund-name {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 14px;
            color: var(--text-primary);
          }
        }
      }
    }
  }

  .toolbar-actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }

  .fund-list-card {
    padding: 14px 16px 16px;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-light);

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;

      .title {
        font-size: 16px;
        font-weight: 800;
        color: var(--text-primary);
      }

      .header-loading {
        color: var(--primary-color);
      }
    }
  }

  .fund-identity {
    display: grid;
    grid-template-columns: 78px minmax(0, 1fr);
    align-items: center;
    gap: 11px;
    min-width: 0;
  }

  .fund-code-pill {
    height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-sm);
    background: var(--bg-hover);
    color: var(--primary-color);
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 850;
  }

  .fund-name-text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 760;
  }

  .nav-cell {
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 850;
  }

  .change-pill {
    height: 28px;
    min-width: 76px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 3px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-light);
    background: var(--bg-hover);
    color: var(--text-secondary);
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 850;

    &.is-up {
      border-color: color-mix(in srgb, var(--success-color) 18%, transparent);
      background: var(--success-light);
      color: var(--success-color);
    }

    &.is-down {
      border-color: color-mix(in srgb, var(--danger-color) 18%, transparent);
      background: var(--danger-light);
      color: var(--danger-color);
    }
  }

  .time-cell {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;

    span {
      color: var(--text-primary);
      font-size: 12px;
      font-weight: 700;
    }

    small {
      color: var(--text-secondary);
      font-family: var(--font-mono);
      font-size: 11px;
    }
  }

  .action-icons {
    display: flex;
    justify-content: center;
    gap: 6px;

    .el-button {
      width: 30px;
      height: 30px;
      padding: 0;
      border-color: var(--border-light);

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
        margin-top: 8px;
        font-size: var(--font-size-sm);
        color: var(--text-secondary);
      }
    }
  }

  .status-tag {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    cursor: pointer;
    font-weight: 800;

    &:hover {
      opacity: 0.84;
    }
  }

  .status-dot-inline {
    width: 6px;
    height: 6px;
    border-radius: var(--radius-full);
    background: currentColor;
  }

  .fund-expanded-panel {
    display: grid;
    grid-template-columns: minmax(300px, 0.4fr) minmax(440px, 1fr);
    gap: 16px;
    padding: 16px;
    background:
      linear-gradient(180deg, rgba(37, 99, 235, 0.035), rgba(37, 99, 235, 0)),
      var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    box-shadow: inset 0 1px 0 rgba(37, 99, 235, 0.06);
  }

  .fund-expanded-summary,
  .fund-expanded-chart {
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background: var(--bg-base);
    box-shadow: var(--shadow-light);
  }

  .expanded-title-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;

    h3 {
      margin: 3px 0 0;
      color: var(--text-primary);
      font-size: 17px;
      font-weight: 850;
      line-height: 1.25;
    }
  }

  .expanded-kicker {
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 800;
  }

  .expanded-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 12px;
  }

  .expanded-metric {
    padding: 12px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background: var(--bg-hover);
    transition: border-color var(--transition-fast), background-color var(--transition-fast);

    &:hover {
      border-color: rgba(37, 99, 235, 0.2);
      background: var(--bg-card);
    }

    span {
      display: block;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 700;
    }

    strong {
      display: block;
      margin-top: 4px;
      color: var(--text-primary);
      font-family: var(--font-mono);
      font-size: 17px;
      font-weight: 850;
    }
  }

  .expanded-meta-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;

    div {
      min-width: 0;
      padding: 10px 0;
      border-top: 1px solid var(--border-light);
    }

    span,
    strong {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: var(--text-secondary);
      font-size: 11px;
      font-weight: 700;
    }

    strong {
      margin-top: 3px;
      color: var(--text-primary);
      font-size: 12px;
      font-weight: 800;
    }
  }

  :deep(.fund-table) {
    border-radius: var(--radius-base);
    overflow: hidden;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);

    &::before {
      display: none;
    }

    .el-table__header-wrapper th {
      height: 44px;
      background: var(--bg-hover) !important;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 850;
    }

    .el-table__row {
      background: var(--bg-card);
      transition: background-color var(--transition-fast);

      &:hover > td.el-table__cell {
        background: rgba(37, 99, 235, 0.035) !important;
      }
    }

    .el-table__cell {
      padding: 10px 0;
      border-bottom-color: var(--border-light);
    }

    .el-table__expanded-cell {
      padding: 0 12px 14px;
      background: var(--bg-card);
      box-shadow: inset 0 1px 0 var(--border-light);
    }

    .is-expanded-row > td {
      background: rgba(37, 99, 235, 0.035) !important;
    }

    .el-table__expand-icon {
      color: var(--text-secondary);
    }

    .el-table__expand-icon--expanded {
      color: var(--primary-color);
    }

    .el-tag {
      padding: 0 8px;
      height: 22px;
      line-height: 20px;
      font-size: 11px;
    }
  }

  @media (max-width: 1180px) {
    .fund-expanded-panel {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 760px) {
    .fund-identity,
    .expanded-metrics,
    .expanded-meta-grid {
      grid-template-columns: 1fr;
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

// 数据源对比弹窗样式
.data-source-content {
  .fund-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-light);

    h3 {
      margin: 0;
      font-size: 18px;
      color: var(--text-primary);
    }

    .fund-code {
      font-size: 14px;
      color: var(--text-secondary);
      font-family: monospace;
      background: var(--bg-page);
      padding: 4px 8px;
      border-radius: 4px;
    }
  }

  .data-source-tips {
    margin-top: 20px;
  }
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;

  p {
    margin-top: 12px;
    color: var(--text-secondary);
  }
}

</style>
