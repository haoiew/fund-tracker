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
        </div>
      </div>

      <div v-if="showSearchPanel" class="search-results-panel">
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
          <button
            v-for="item in searchResults"
            :key="item.code"
            type="button"
            class="search-result-item"
            @click="onSearchFundSelect(item)"
          >
            <span class="fund-code">{{ item.code }}</span>
            <span class="fund-name">{{ item.name }}</span>
          </button>
        </div>
      </div>

      <div v-if="searchResultFund" class="search-result-inline">
        <div class="search-result-main">
          <div>
            <span class="expanded-kicker">SEARCH RESULT</span>
            <h3>{{ searchResultFund.name }}</h3>
            <span class="fund-code-pill">{{ searchResultFund.code }}</span>
          </div>
          <div class="search-result-metrics">
            <div>
              <span>估算净值</span>
              <strong :class="getChangeClass(searchResultFund.estimate_change)">
                {{ formatNav(searchResultFund.estimate_nav) }}
              </strong>
            </div>
            <div>
              <span>涨跌幅</span>
              <strong :class="getChangeClass(searchResultFund.estimate_change)">
                {{ formatChange(searchResultFund.estimate_change) }}
              </strong>
            </div>
          </div>
        </div>
        <div class="search-result-actions">
          <el-button text @click="clearSearchResult">关闭</el-button>
          <el-button type="success" @click="addSearchFundToWatchlist">添加关注</el-button>
          <el-button type="primary" @click="addSearchFundToPortfolio">添加持仓</el-button>
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
            <div v-if="expandedPanelMode === 'detail'" class="fund-expanded-panel">
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
                    <strong :class="getFundChangeClass(row)">{{ formatNav(row.estimate_nav) }}</strong>
                  </div>
                  <div class="expanded-metric">
                    <span>{{ row.is_realtime === false ? '净值涨跌' : '实时涨跌' }}</span>
                    <strong :class="getFundChangeClass(row)">{{ formatChange(row.estimate_change) }}</strong>
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
                    <strong>{{ getFundDataSourceName(row) }}</strong>
                    <small v-if="row.data_source_description">{{ row.data_source_description }}</small>
                  </div>
                  <div>
                    <span>行情类型</span>
                    <strong>{{ getFundDataKindLabel(row) }}</strong>
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

            <div v-else class="data-source-inline-panel">
              <div class="data-source-panel-header">
                <div>
                  <span class="expanded-kicker">DATA SOURCES</span>
                  <h3>{{ dataSourceData?.name || row.name }}</h3>
                  <span class="fund-code-pill">{{ row.code }}</span>
                </div>
                <div class="data-source-header-side">
                  <div v-if="dataSourceData" class="data-source-mini-meta">
                    <span>Auto</span>
                    <strong>{{ getBestSourceName() }}</strong>
                    <em>{{ dataSourceData.total_sources }} sources</em>
                  </div>
                  <el-button text size="small" @click="collapseFundDetail">收起</el-button>
                </div>
              </div>

              <div v-if="dataSourceLoading" class="loading-container inline-loading">
                <el-icon class="is-loading" size="24"><Loading /></el-icon>
                <p>正在加载数据源...</p>
              </div>

              <template v-else-if="dataSourceData">
                <el-table :data="dataSourceData.sources" class="data-source-table" style="width: 100%" border>
                  <el-table-column label="数据源" min-width="260">
                    <template #default="{ row: sourceRow }">
                      <div class="source-name-cell">
                        <strong>{{ getSourceRowName(sourceRow) }}</strong>
                        <small>{{ getSourceRowMeta(sourceRow) }}</small>
                        <em v-if="sourceRow.description">{{ sourceRow.description }}</em>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="estimate_nav" label="估算净值" width="116" align="right">
                    <template #default="{ row: sourceRow }">
                      <span :class="getChangeClass(sourceRow.estimate_change_pct)">
                        {{ formatNav(sourceRow.estimate_nav) }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="estimate_change_pct" label="涨跌幅" width="112" align="right">
                    <template #default="{ row: sourceRow }">
                      <span :class="getSourceChangeClass(sourceRow)">
                        {{ formatChange(sourceRow.estimate_change_pct) }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column label="更新时间" min-width="160">
                    <template #default="{ row: sourceRow }">
                      <div class="source-time-cell">
                        <span>{{ sourceRow.update_time || '--' }}</span>
                        <small>{{ sourceRow.is_realtime ? '盘中估算时刻' : '净值公布日期' }}</small>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="is_fresh" label="状态" width="96" align="center">
                    <template #default="{ row: sourceRow }">
                      <el-tooltip v-if="!sourceRow.is_fresh" :content="sourceRow.error || '数据源当前不可用'" placement="top">
                        <el-tag type="warning" size="small">不可用</el-tag>
                      </el-tooltip>
                      <el-tag v-else type="success" size="small">可用</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="104" align="center">
                    <template #default="{ row: sourceRow }">
                      <el-button
                        type="primary"
                        size="small"
                        :disabled="!sourceRow.is_fresh || sourceRow.source === row.data_source"
                        @click="selectDataSource(sourceRow.source)"
                      >
                        {{ sourceRow.source === row.data_source ? '当前' : '采用' }}
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>

                <div v-if="alternativesLoading" class="alternative-section">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>正在评估替代估算...</span>
                </div>

                <div v-else-if="realtimeAlternatives && !realtimeAlternatives.skipped" class="alternative-section">
                  <div class="alternative-header">
                    <div>
                      <span class="expanded-kicker">FALLBACK ESTIMATE</span>
                      <h4>替代实时估算</h4>
                    </div>
                    <el-tag type="warning" size="small">非官方实时估值</el-tag>
                  </div>

                  <div v-if="realtimeAlternatives.holdings_based_estimate?.feasible" class="holding-estimate-row">
                    <div>
                      <strong :class="getChangeClass(realtimeAlternatives.holdings_based_estimate.weighted_stock_change_pct ?? null)">
                        {{ formatChange(realtimeAlternatives.holdings_based_estimate.weighted_stock_change_pct ?? null) }}
                      </strong>
                      <span>
                        持仓日期 {{ realtimeAlternatives.holdings_based_estimate.position_date || '--' }} ·
                        报价覆盖 {{ formatPercentRatio(realtimeAlternatives.holdings_based_estimate.quoted_weight_coverage) }} ·
                        {{ realtimeAlternatives.holdings_based_estimate.quoted_count || 0 }}/{{ realtimeAlternatives.holdings_based_estimate.holding_count || 0 }} 只
                      </span>
                    </div>
                    <el-button size="small" type="warning" plain @click="selectHoldingEstimate">
                      采用估算
                    </el-button>
                  </div>

                  <el-alert
                    v-else
                    type="warning"
                    :closable="false"
                    show-icon
                    title="暂未形成可用持仓估算"
                  >
                    <template #default>
                      {{ realtimeAlternatives.holdings_based_estimate?.reason || '缺少可解析持仓或实时股票报价覆盖不足' }}
                    </template>
                  </el-alert>

                  <div v-if="realtimeAlternatives.fallback_estimate?.feasible" class="holding-estimate-row">
                    <div>
                      <strong :class="getChangeClass(realtimeAlternatives.fallback_estimate.change_pct ?? null)">
                        {{ formatChange(realtimeAlternatives.fallback_estimate.change_pct ?? null) }}
                      </strong>
                      <span>
                        {{ realtimeAlternatives.fallback_estimate.source === 'tencent' ? '腾讯基金行情' : '最新净值涨跌幅' }} ·
                        {{ realtimeAlternatives.fallback_estimate.update_time || '--' }}
                      </span>
                    </div>
                    <el-button size="small" type="warning" plain @click="selectFallbackEstimate">
                      采用兜底
                    </el-button>
                  </div>

                  <div v-if="realtimeAlternatives.reference_symbol_estimate?.feasible" class="holding-estimate-row">
                    <div>
                      <strong :class="getChangeClass(realtimeAlternatives.reference_symbol_estimate.weighted_stock_change_pct ?? null)">
                        {{ formatChange(realtimeAlternatives.reference_symbol_estimate.weighted_stock_change_pct ?? null) }}
                      </strong>
                      <span>
                        {{ realtimeAlternatives.reference_symbol_estimate.references?.map(ref => ref.name).join('、') || '参考标的' }}
                      </span>
                    </div>
                    <el-button size="small" type="warning" plain @click="selectReferenceEstimate">
                      采用标的
                    </el-button>
                  </div>

                  <div v-if="realtimeAlternatives.same_name_realtime_candidates.length" class="candidate-strip">
                    <span>相近基金实时参考</span>
                    <button
                      v-for="candidate in realtimeAlternatives.same_name_realtime_candidates"
                      :key="candidate.code"
                      type="button"
                      @click="applyCandidateRealtime(candidate)"
                    >
                      {{ candidate.code }} {{ formatChange(candidate.change_pct) }}
                    </button>
                  </div>
                </div>
              </template>

              <el-empty v-else description="暂无数据源结果" />
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
            <div class="nav-cell" :class="getFundChangeClass(row)">
              {{ formatNav(row.estimate_nav) }}
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="estimate_change" label="涨跌幅" width="112" align="right" sortable>
          <template #default="{ row }">
            <el-tooltip :content="getChangeTooltip(row)" placement="top" :disabled="!getChangeTooltip(row)">
              <div class="change-pill" :class="getFundChangeTone(row)">
                <el-icon v-if="row.is_realtime !== false && row.estimate_change > 0" size="12"><ArrowUp /></el-icon>
                <el-icon v-else-if="row.is_realtime !== false && row.estimate_change < 0" size="12"><ArrowDown /></el-icon>
                <span>{{ formatChange(row.estimate_change) }}</span>
              </div>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column prop="update_time" label="更新时间" width="154">
          <template #default="{ row }">
            <div class="time-cell">
              <span>{{ row.update_time || '--' }}</span>
              <small>{{ getFundDataSourceShortName(row) }}</small>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="104" align="center">
          <template #default="{ row }">
            <el-tooltip placement="top">
              <template #content>
                  <div style="font-size: 12px;">
                    <div>数据来源: {{ getFundDataSourceName(row) }}</div>
                    <div>行情类型: {{ getFundDataKindLabel(row) }}</div>
                    <div v-if="row.data_timestamp">更新时间: {{ formatDateTime(row.data_timestamp) }}</div>
                    <div style="color: #409eff; margin-top: 4px;">点击展开数据源对比</div>
                  </div>
                </template>
              <el-tag 
                :type="getStatusType(row.status)" 
                size="small" 
                effect="light" 
                class="status-tag"
                :class="{ 'is-active': expandedPanelMode === 'dataSource' && isFundExpanded(row) }"
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
import { ArrowUp, ArrowDown, Search, Refresh, Wallet, Loading, Download, View, Plus, Check, DataLine, Coin, TrendCharts as TrendChartsIcon, InfoFilled, Delete } from '@element-plus/icons-vue'
import type { TableInstance } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { useFundStore } from '@/stores/fundStore'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { dataManager } from '@/stores/dataManager'
import { ElMessage, ElMessageBox } from 'element-plus'
import FundChart from '@/components/Charts/FundChart.vue'
import { exportFundsToCSV } from '@/utils/export'
import fundApi, { type FundRealtimeData, type FundSearchItem, type RealtimeAlternativeResult } from '@/api/fund'

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
const showSearchResults = ref(false)
const searchDebounceTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const isSearchInProgress = ref(false)
const showSearchPanel = computed(() => showSearchResults.value || searchLoading.value || searchResults.value.length > 0 || searchInputValue.value.trim().length >= 2)

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

const searchResultFund = ref<FundRealtimeData | null>(null)

const dataSourceLoading = ref(false)
const alternativesLoading = ref(false)
const expandedPanelMode = ref<'detail' | 'dataSource'>('detail')

interface DataSourceComparisonItem {
  source: string
  display_name?: string
  short_name?: string
  description?: string
  priority: number
  name?: string | null
  estimate_nav: number | null
  estimate_change_pct: number | null
  last_nav: number | null
  last_change_pct: number | null
  update_time: string
  data_kind?: 'realtime_estimate' | 'latest_nav'
  data_kind_label?: string
  is_realtime?: boolean
  is_fresh: boolean
  error?: string | null
}

const dataSourceData = ref<{
  code: string
  name: string
  sources: DataSourceComparisonItem[]
  best_source: string | null
  best_source_display_name?: string | null
  total_sources: number
} | null>(null)
const currentDataSourceFund = ref<FundRealtimeData | null>(null)
const realtimeAlternatives = ref<RealtimeAlternativeResult | null>(null)

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

const formatPercentRatio = (val?: number | null) => {
  if (val === null || val === undefined || isNaN(Number(val))) return '--'
  return `${(Number(val) * 100).toFixed(0)}%`
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

const DATA_SOURCE_FALLBACK_NAMES: Record<string, string> = {
  tiantian: '天天基金盘中估值接口',
  efinance: 'EFinance 批量基金行情接口',
  tencent: '腾讯基金行情',
  eastmoney_lsjz: '东方财富历史净值接口',
  pingzhongdata: '东方财富基金页面数据'
}

const DATA_SOURCE_SHORT_NAMES: Record<string, string> = {
  tiantian: 'TTFund',
  efinance: 'EFinance',
  tencent: 'Tencent',
  eastmoney_lsjz: 'Eastmoney',
  pingzhongdata: 'Eastmoney'
}

const getDataSourceDisplayName = (source?: string | null, displayName?: string | null): string => {
  if (displayName) return displayName
  if (!source) return '自动选择'
  return DATA_SOURCE_FALLBACK_NAMES[source] || source
}

const getDataSourceShortName = (source?: string | null, shortName?: string | null): string => {
  if (shortName) return shortName
  if (!source) return 'Auto'
  return DATA_SOURCE_SHORT_NAMES[source] || source
}

const getFundDataSourceName = (fund: FundRealtimeData): string => {
  return getDataSourceDisplayName(fund.data_source, fund.data_source_display_name)
}

const getFundDataSourceShortName = (fund: FundRealtimeData): string => {
  return getDataSourceShortName(fund.data_source, fund.data_source_short_name)
}

const getFundDataKindLabel = (fund: FundRealtimeData): string => {
  return fund.data_kind_label || (fund.is_realtime ? '实时估值' : '最新净值')
}

const getSourceRowName = (sourceRow: DataSourceComparisonItem): string => {
  return sourceRow.display_name || getDataSourceDisplayName(sourceRow.source)
}

const getSourceRowMeta = (sourceRow: DataSourceComparisonItem): string => {
  const dataKind = sourceRow.data_kind_label || (sourceRow.is_realtime ? '实时估值' : '最新净值')
  const shortName = getDataSourceShortName(sourceRow.source, sourceRow.short_name)
  return `${shortName} · ${dataKind}`
}

const getBestSourceName = (): string => {
  if (!dataSourceData.value?.best_source) return '无可用数据源'
  return getDataSourceDisplayName(dataSourceData.value.best_source, dataSourceData.value.best_source_display_name)
}

const isHoldingEstimateData = (row: Pick<FundRealtimeData, 'data_kind'> | DataSourceComparisonItem): boolean => {
  return row.data_kind === 'holdings_estimate'
}

const isSimilarReferenceData = (row: Pick<FundRealtimeData, 'data_kind'> | DataSourceComparisonItem): boolean => {
  return row.data_kind === 'similar_realtime_reference'
}

const isReferenceEstimateData = (row: Pick<FundRealtimeData, 'data_kind'> | DataSourceComparisonItem): boolean => {
  return row.data_kind === 'reference_symbol_estimate'
}

const isFallbackEstimateData = (row: Pick<FundRealtimeData, 'data_kind'> | DataSourceComparisonItem): boolean => {
  return row.data_kind === 'fallback_estimate'
}

const isLatestNavData = (row: Pick<FundRealtimeData, 'data_kind' | 'is_realtime'> | DataSourceComparisonItem): boolean => {
  return row.data_kind === 'latest_nav' || (!row.data_kind && row.is_realtime === false)
}

const getFundChangeClass = (fund: FundRealtimeData): string => {
  if (isHoldingEstimateData(fund) || isReferenceEstimateData(fund) || isSimilarReferenceData(fund) || isFallbackEstimateData(fund)) return getChangeClass(fund.estimate_change)
  if (isLatestNavData(fund)) return 'text-muted-change'
  return getChangeClass(fund.estimate_change)
}

const getSourceChangeClass = (sourceRow: DataSourceComparisonItem): string => {
  if (isLatestNavData(sourceRow)) return 'text-muted-change'
  return getChangeClass(sourceRow.estimate_change_pct)
}

const getFundChangeTone = (fund: FundRealtimeData): string => {
  if (isHoldingEstimateData(fund)) return 'is-holdings-estimate'
  if (isReferenceEstimateData(fund)) return 'is-reference-estimate'
  if (isSimilarReferenceData(fund)) return 'is-similar-reference'
  if (isFallbackEstimateData(fund)) return 'is-fallback-estimate'
  if (isLatestNavData(fund)) return 'is-latest-nav'
  return getChangeTone(fund.estimate_change)
}

const getChangeTooltip = (fund: FundRealtimeData): string => {
  if (isHoldingEstimateData(fund)) return fund.data_source_description || '基于最新披露持仓和实时股票行情的替代估算，不是基金公司发布的盘中估值。'
  if (isReferenceEstimateData(fund)) return fund.data_source_description || '采用明确跟踪标的或场内份额行情作为自动参考，不是基金公司发布的盘中估值。'
  if (isSimilarReferenceData(fund)) return fund.data_source_description || '采用相近基金实时涨跌幅作为人工参考，不是本基金自身估值。'
  if (isFallbackEstimateData(fund)) return fund.data_source_description || '采用净值或报价源涨跌幅作为兜底参考，不是基金公司发布的盘中估值。'
  if (!isLatestNavData(fund)) return ''
  return '该涨跌幅来自最新公布净值相对上一交易日的日增长率，不是盘中实时估值。'
}

// 获取状态标签类型
const getStatusType = (status: string): 'success' | 'info' | 'warning' | 'danger' => {
  if (status === '正常') return 'success'
  if (status === '最新净值') return 'info'
  if (status === '场内行情') return 'warning'
  if (status === '持仓估算') return 'warning'
  if (status === '标的估算') return 'warning'
  if (status === '相近参考') return 'warning'
  if (status === '兜底估算') return 'warning'
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
  searchResultFund.value = null

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
  } catch (e) {
    console.error('获取基金详情失败:', e)
    ElMessage.error('获取基金详情失败')
  }
}

const clearSearchResult = () => {
  searchResultFund.value = null
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
    searchResultFund.value = null
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

  searchResultFund.value = null
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
  if (isFundExpanded(fund) && expandedPanelMode.value === 'detail') {
    collapseFundDetail()
    return
  }
  expandedPanelMode.value = 'detail'
  expandedRowKeys.value = [fund.code]
}

const collapseFundDetail = () => {
  expandedRowKeys.value = []
  dataSourceLoading.value = false
  alternativesLoading.value = false
  currentDataSourceFund.value = null
  realtimeAlternatives.value = null
}

const handleExpandChange = (row: FundRealtimeData, expandedRows: FundRealtimeData[]) => {
  const isExpanded = expandedRows.some(item => item.code === row.code)
  expandedRowKeys.value = isExpanded ? [row.code] : []
  if (isExpanded && !(expandedPanelMode.value === 'dataSource' && currentDataSourceFund.value?.code === row.code)) {
    expandedPanelMode.value = 'detail'
  }
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
const selectDataSource = (source: string) => {
  const fund = currentDataSourceFund.value
  const selectedSource = dataSourceData.value?.sources.find(item => item.source === source)
  if (!fund || !selectedSource) return

  if (!selectedSource.is_fresh) {
    ElMessage.warning(`${source} 当前不可用`)
    return
  }

  const updatedFund = {
    ...fund,
    estimate_nav: selectedSource.estimate_nav,
    estimate_change: selectedSource.estimate_change_pct,
    update_time: selectedSource.update_time || fund.update_time,
    status: selectedSource.is_realtime ? '正常' : (selectedSource.data_kind_label || '最新净值'),
    data_source: selectedSource.source,
    data_source_display_name: selectedSource.display_name,
    data_source_short_name: selectedSource.short_name,
    data_source_description: selectedSource.description,
    data_kind: selectedSource.data_kind,
    data_kind_label: selectedSource.data_kind_label,
    is_realtime: selectedSource.is_realtime,
    data_timestamp: new Date().toISOString()
  }

  dataManager.updateRealtimeItem(updatedFund)
  currentDataSourceFund.value = updatedFund
  ElMessage.success(`当前行已采用 ${getDataSourceDisplayName(selectedSource.source, selectedSource.display_name)} 数据`)
}

const selectHoldingEstimate = () => {
  const fund = currentDataSourceFund.value
  const estimate = realtimeAlternatives.value?.holdings_based_estimate
  if (!fund || !estimate?.feasible || estimate.weighted_stock_change_pct === null || estimate.weighted_stock_change_pct === undefined) return

  const updatedFund = {
    ...fund,
    estimate_change: estimate.weighted_stock_change_pct,
    status: '持仓估算',
    data_source: 'holdings_estimate',
    data_source_display_name: '持仓实时估算',
    data_source_short_name: 'Holdings',
    data_source_description: `基于 ${estimate.position_date || '最新披露'} 十大持仓和实时股票行情的加权估算，报价覆盖 ${formatPercentRatio(estimate.quoted_weight_coverage)}。`,
    data_kind: 'holdings_estimate' as const,
    data_kind_label: '持仓估算',
    is_realtime: false,
    data_timestamp: new Date().toISOString()
  }

  dataManager.updateRealtimeItem(updatedFund)
  currentDataSourceFund.value = updatedFund
  ElMessage.success('当前行已采用持仓估算涨跌幅')
}

const selectFallbackEstimate = () => {
  const fund = currentDataSourceFund.value
  const fallback = realtimeAlternatives.value?.fallback_estimate
  if (!fund || !fallback?.feasible || fallback.change_pct === null || fallback.change_pct === undefined) return

  const updatedFund = {
    ...fund,
    estimate_change: fallback.change_pct,
    update_time: fallback.update_time || fund.update_time,
    status: '兜底估算',
    data_source: fallback.source || 'fallback_estimate',
    data_source_display_name: '净值/行情兜底估算',
    data_source_short_name: 'Fallback',
    data_source_description: `持仓穿透不可用，使用${fallback.source === 'tencent' ? '腾讯基金行情' : '最新净值涨跌幅'}作为估算参考。`,
    data_kind: 'fallback_estimate' as const,
    data_kind_label: '兜底估算',
    is_realtime: false,
    data_timestamp: new Date().toISOString()
  }

  dataManager.updateRealtimeItem(updatedFund)
  currentDataSourceFund.value = updatedFund
  ElMessage.success('当前行已采用兜底估算涨跌幅')
}

const selectReferenceEstimate = () => {
  const fund = currentDataSourceFund.value
  const reference = realtimeAlternatives.value?.reference_symbol_estimate
  if (!fund || !reference?.feasible || reference.weighted_stock_change_pct === null || reference.weighted_stock_change_pct === undefined) return

  const updatedFund = {
    ...fund,
    estimate_change: reference.weighted_stock_change_pct,
    update_time: new Date().toLocaleString('zh-CN', { hour12: false }),
    status: '标的估算',
    data_source: 'reference_symbol_estimate',
    data_source_display_name: '引用标的估算',
    data_source_short_name: 'Reference',
    data_source_description: `持仓穿透不足，使用 ${reference.references?.map(ref => ref.name).join('、') || '参考标的'} 行情估算。`,
    data_kind: 'reference_symbol_estimate' as const,
    data_kind_label: '标的估算',
    is_realtime: false,
    data_timestamp: new Date().toISOString()
  }

  dataManager.updateRealtimeItem(updatedFund)
  currentDataSourceFund.value = updatedFund
  ElMessage.success('当前行已采用引用标的估算涨跌幅')
}

const applyCandidateRealtime = (candidate: RealtimeAlternativeResult['same_name_realtime_candidates'][number]) => {
  const fund = currentDataSourceFund.value
  if (!fund) return

  const updatedFund = {
    ...fund,
    estimate_change: candidate.change_pct,
    update_time: candidate.update_time || fund.update_time,
    status: '相近参考',
    data_source: candidate.source,
    data_source_display_name: `相近基金参考：${candidate.name}`,
    data_source_short_name: 'Similar',
    data_source_description: `采用相近基金 ${candidate.code} ${candidate.name} 的实时涨跌幅作为人工参考。`,
    data_kind: 'similar_realtime_reference' as const,
    data_kind_label: '相近参考',
    is_realtime: false,
    data_timestamp: new Date().toISOString()
  }

  dataManager.updateRealtimeItem(updatedFund)
  currentDataSourceFund.value = updatedFund
  ElMessage.success(`当前行已采用 ${candidate.code} 相近基金参考`)
}

// 显示数据源菜单
const showDataSourceMenu = async (fund: FundRealtimeData) => {
  console.log('点击状态标签，基金:', fund.code, fund.name)
  if (isFundExpanded(fund) && expandedPanelMode.value === 'dataSource') {
    collapseFundDetail()
    return
  }

  currentDataSourceFund.value = fund
  expandedPanelMode.value = 'dataSource'
  expandedRowKeys.value = [fund.code]
  dataSourceData.value = null
  realtimeAlternatives.value = null
  dataSourceLoading.value = true
  alternativesLoading.value = fund.is_realtime === false
  
  try {
    console.log('正在获取数据源对比...')
    const [result, alternatives] = await Promise.all([
      fundApi.getDataSources(fund.code, fund.name),
      fund.is_realtime === false ? fundApi.getRealtimeAlternatives(fund.code, fund.name) : Promise.resolve(null)
    ])
    console.log('数据源对比结果:', result)
    dataSourceData.value = result
    realtimeAlternatives.value = alternatives
  } catch (error) {
    console.error('获取数据源对比失败:', error)
    ElMessage.error('获取数据源对比失败')
  } finally {
    dataSourceLoading.value = false
    alternativesLoading.value = false
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
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .search-toolbar {
    gap: 12px;
  }

  .search-box {
    flex: 1;
    min-width: 280px;
    max-width: 560px;

    .search-input {
      width: 100%;
    }
  }

  .search-results-panel {
    width: min(100%, 560px);
    max-height: 320px;
    overflow-y: auto;
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    box-shadow: var(--shadow-light);

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
      padding: 6px;

      .search-result-item {
        width: 100%;
        min-height: 38px;
        display: grid;
        grid-template-columns: 78px minmax(0, 1fr);
        align-items: center;
        gap: 12px;
        padding: 8px 10px;
        border: 0;
        border-radius: var(--radius-sm);
        background: transparent;
        cursor: pointer;
        transition: background-color var(--transition-fast);

        &:hover {
          background: var(--bg-hover);
        }

        .fund-code {
          font-family: var(--font-mono);
          font-size: 12px;
          color: var(--primary-color);
          font-weight: 800;
        }

        .fund-name {
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          text-align: left;
          font-size: 14px;
          color: var(--text-primary);
        }
      }
    }
  }

  .search-result-inline {
    width: min(100%, 760px);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background: var(--bg-card);
    box-shadow: var(--shadow-light);
  }

  .search-result-main {
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 18px;

    h3 {
      margin: 2px 0 6px;
      color: var(--text-primary);
      font-size: 16px;
      font-weight: 850;
      line-height: 1.25;
    }
  }

  .search-result-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(92px, 1fr));
    gap: 8px;

    div {
      padding: 9px 10px;
      border: 1px solid var(--border-light);
      border-radius: var(--radius-sm);
      background: var(--bg-hover);
    }

    span,
    strong {
      display: block;
      white-space: nowrap;
    }

    span {
      color: var(--text-secondary);
      font-size: 11px;
      font-weight: 700;
    }

    strong {
      margin-top: 2px;
      font-family: var(--font-mono);
      font-size: 15px;
      font-weight: 850;
    }
  }

  .search-result-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
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

    &.is-latest-nav {
      border-color: var(--border-light);
      background: #f1f5f9;
      color: #64748b;
    }

    &.is-holdings-estimate {
      border-color: #fed7aa;
      background: #fff7ed;
      color: #c2410c;
    }

    &.is-reference-estimate {
      border-color: #bae6fd;
      background: #f0f9ff;
      color: #0369a1;
    }

    &.is-similar-reference {
      border-color: #bfdbfe;
      background: #eff6ff;
      color: #2563eb;
    }

    &.is-fallback-estimate {
      border-color: #e9d5ff;
      background: #faf5ff;
      color: #7e22ce;
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
    min-width: 68px;
    height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    box-sizing: border-box;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-weight: 800;
    line-height: 1;
    vertical-align: middle;
    transition: background-color var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);

    &:hover {
      opacity: 0.84;
    }

    &.is-active {
      box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.32);
      background: rgba(37, 99, 235, 0.06);
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

  .data-source-inline-panel {
    min-width: 0;
    padding: 16px;
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    box-shadow: inset 0 1px 0 rgba(37, 99, 235, 0.06);
  }

  .data-source-panel-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;

    h3 {
      margin: 3px 0 8px;
      color: var(--text-primary);
      font-size: 17px;
      font-weight: 850;
      line-height: 1.25;
    }
  }

  .data-source-header-side {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .data-source-mini-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    min-height: 24px;
    color: var(--text-secondary);
    font-size: 12px;
    white-space: nowrap;

    span {
      color: var(--text-secondary);
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 800;
    }

    strong {
      color: var(--text-primary);
      font-size: 12px;
      font-weight: 850;
    }

    em {
      color: var(--text-secondary);
      font-size: 11px;
      font-style: normal;
    }
  }

  .data-source-table {
    border-radius: var(--radius-base);
    overflow: hidden;

    :deep(.el-tag) {
      min-width: 52px;
      height: 24px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-sizing: border-box;
      border-radius: var(--radius-sm);
      line-height: 1;
      font-weight: 800;
      vertical-align: middle;
    }

    :deep(.el-button) {
      min-width: 54px;
      height: 28px;
      box-sizing: border-box;
      border-radius: var(--radius-sm);
      font-weight: 800;
      line-height: 1;
    }

    :deep(.el-button.is-disabled) {
      opacity: 0.72;
    }
  }

  .source-name-cell,
  .source-time-cell {
    display: flex;
    flex-direction: column;
    gap: 3px;
    min-width: 0;

    strong,
    span {
      color: var(--text-primary);
      font-size: 13px;
      font-weight: 700;
      line-height: 1.25;
    }

    small {
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 600;
      line-height: 1.2;
    }

    em {
      color: var(--text-secondary);
      display: -webkit-box;
      overflow: hidden;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      font-size: 11px;
      font-style: normal;
      line-height: 1.35;
    }
  }

  .alternative-section {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border-light);
    display: flex;
    flex-direction: column;
    gap: 10px;
    color: var(--text-secondary);
    font-size: 12px;
  }

  .alternative-header,
  .holding-estimate-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .alternative-header {
    h4 {
      margin: 3px 0 0;
      color: var(--text-primary);
      font-size: 14px;
      font-weight: 850;
    }
  }

  .holding-estimate-row {
    padding: 10px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-sm);
    background: var(--bg-hover);

    div {
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    strong {
      font-family: var(--font-mono);
      font-size: 18px;
      font-weight: 900;
    }

    span {
      color: var(--text-secondary);
      line-height: 1.4;
    }
  }

  .candidate-strip {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;

    span {
      color: var(--text-secondary);
      font-weight: 700;
    }

    button {
      height: 26px;
      padding: 0 8px;
      border: 1px solid var(--border-light);
      border-radius: var(--radius-sm);
      background: var(--bg-card);
      color: var(--text-primary);
      cursor: pointer;
      font-family: var(--font-mono);
      font-size: 12px;
    }
  }

  .inline-loading {
    min-height: 150px;
    padding: 24px;
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

    small {
      display: block;
      margin-top: 4px;
      color: var(--text-secondary);
      font-size: 11px;
      line-height: 1.35;
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

    .el-table__body .el-table__cell {
      overflow: visible;
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

    .search-result-inline,
    .search-result-main {
      align-items: stretch;
      flex-direction: column;
    }

    .search-result-metrics {
      grid-template-columns: 1fr;
    }

    .search-result-actions {
      justify-content: flex-start;
    }
  }
}

.text-success {
  color: var(--success-color);
}

.text-danger {
  color: var(--danger-color);
}

.text-muted-change {
  color: #64748b;
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
