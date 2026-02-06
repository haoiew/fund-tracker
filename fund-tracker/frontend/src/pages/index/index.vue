<template>
  <div class="container">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <input
        class="search-input"
        type="text"
        placeholder="搜索基金代码或名称"
        v-model="searchKeyword"
        @keyup.enter="handleSearch"
      />
      <button class="search-btn" @click="handleSearch">搜索</button>
    </div>

    <!-- 市场概览 -->
    <div class="market-overview">
      <div class="overview-title">市场概览</div>
      <div class="overview-stats">
        <div class="stat-item">
          <span class="stat-value" :class="upFunds.length > 0 ? 'up' : ''">{{upFunds.length}}</span>
          <span class="stat-label">上涨</span>
        </div>
        <div class="stat-item">
          <span class="stat-value" :class="downFunds.length > 0 ? 'down' : ''">{{downFunds.length}}</span>
          <span class="stat-label">下跌</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{fundCodes.length}}</span>
          <span class="stat-label">关注</span>
        </div>
      </div>
    </div>

    <!-- 基金列表 -->
    <div class="fund-list">
      <div class="list-header">
        <span class="header-title">基金实时估值</span>
        <div class="filter-tabs">
          <span class="tab active">全部</span>
          <span class="tab">上涨</span>
          <span class="tab">下跌</span>
        </div>
      </div>

      <!-- 表格头部 -->
      <div class="table-header">
        <div class="th col-code">基金代码</div>
        <div class="th col-name">基金名称</div>
        <div class="th col-nav">估算净值</div>
        <div class="th col-change">涨跌幅</div>
        <div class="th col-time">更新时间</div>
        <div class="th col-status">状态</div>
        <div class="th col-actions">操作</div>
      </div>

      <!-- 表格内容 -->
      <div class="table-body">
        <div
          class="table-row"
          v-for="code in fundCodes"
          :key="code"
          :class="{ 'loading': isLoading(code) }"
        >
          <div class="td col-code">{{code}}</div>
          <div class="td col-name">
            <span class="fund-name-text">{{realtimeData[code]?.name || code}}</span>
          </div>
          <div class="td col-nav" :class="getNavClass(code)">
            {{formatNav(realtimeData[code]?.estimate_nav)}}
          </div>
          <div class="td col-change" :class="getChangeClass(realtimeData[code]?.estimate_change)">
            {{formatChange(realtimeData[code]?.estimate_change)}}
          </div>
          <div class="td col-time">{{realtimeData[code]?.update_time || '--'}}</div>
          <div class="td col-status">
            <span class="status-tag" :class="getStatusClass(code)">
              {{getStatusText(code)}}
            </span>
            <span v-if="realtimeData[code]?.data_source && realtimeData[code]?.data_source !== 'unknown'"
                  class="source-tag"
                  :title="'数据源: ' + realtimeData[code]?.data_source">
              {{realtimeData[code]?.data_source}}
            </span>
          </div>
          <div class="td col-actions">
            <div class="action-btns">
              <button class="icon-btn detail" @click.stop="goToDetail(code)" title="详情">
                <svg viewBox="0 0 24 24" width="14" height="14">
                  <path fill="currentColor" d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
                </svg>
              </button>
              <button class="icon-btn add" @click.stop="addToPortfolio(code)" title="添加">
                <svg viewBox="0 0 24 24" width="14" height="14">
                  <path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                </svg>
              </button>
              <button class="icon-btn delete" @click.stop="removeFund(code)" title="删除">
                <svg viewBox="0 0 24 24" width="14" height="14">
                  <path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加基金弹窗 -->
    <div class="modal" v-if="showAddModal" @click="showAddModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <span class="modal-title">添加基金</span>
          <span class="modal-close" @click="showAddModal = false">×</span>
        </div>
        <div class="modal-body">
          <input
            class="fund-input"
            type="text"
            placeholder="输入基金代码"
            v-model="newFundCode"
          />
          <button class="confirm-btn" @click="addFund">确认添加</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useFundStore } from '../../stores/fundStore.js'

const fundStore = useFundStore()
const searchKeyword = ref('')
const showAddModal = ref(false)
const newFundCode = ref('')

// 基金代码列表（本地存储）
const fundCodes = ref(['016531', '017436', '018125', '012349', '015916', '007722', '160125', '501018'])

const realtimeData = computed(() => fundStore.realtimeData)
const upFunds = computed(() => fundStore.upFunds)
const downFunds = computed(() => fundStore.downFunds)

onMounted(() => {
  loadRealtimeData()
  // 定时刷新
  setInterval(loadRealtimeData, 60000)
})

const loadRealtimeData = async () => {
  await fundStore.fetchRealtimeData(fundCodes.value)
}

const isLoading = (code) => {
  const data = realtimeData.value[code]
  if (!data) return true
  return data.status === '获取中' || data.status === '获取失败'
}

const getStatusText = (code) => {
  const data = realtimeData.value[code]
  if (!data) return '获取中'

  // 如果有净值数据，显示正常
  if (data.estimate_nav !== null && data.estimate_nav !== undefined) {
    return '正常'
  }

  // 如果数据源是最新净值，显示最新净值
  if (data.data_source === '最新净值' || data.status === '最新净值') {
    return '最新净值'
  }

  // 如果是QDII/LOF基金，显示对应状态
  if (data.status && data.status !== '获取中') {
    return data.status
  }

  return '获取中'
}

const getStatusClass = (code) => {
  const text = getStatusText(code)
  if (text === '正常') return 'status-normal'
  if (text === '最新净值') return 'status-nav'
  if (text === '获取中') return 'status-loading'
  if (text === '获取失败') return 'status-error'
  return 'status-other'
}

const getNavClass = (code) => {
  const data = realtimeData.value[code]
  if (!data || data.estimate_nav === null) return 'nav-empty'
  return ''
}

const handleSearch = async () => {
  if (!searchKeyword.value) return
  const results = await fundStore.searchFunds(searchKeyword.value)
  if (results.length > 0) {
    alert(`找到基金: ${results[0].name} (${results[0].code})`)
  }
}

const goToDetail = (code) => {
  alert(`查看基金详情: ${code}`)
}

const addToPortfolio = (code) => {
  alert(`添加基金到持仓: ${code}`)
}

const removeFund = (code) => {
  if (confirm(`确定要删除基金 ${code} 吗？`)) {
    fundCodes.value = fundCodes.value.filter(c => c !== code)
    delete realtimeData.value[code]
  }
}

const addFund = () => {
  if (newFundCode.value && !fundCodes.value.includes(newFundCode.value)) {
    fundCodes.value.push(newFundCode.value)
    newFundCode.value = ''
    showAddModal.value = false
    loadRealtimeData()
  }
}

const getChangeClass = (change) => {
  if (!change) return ''
  return change > 0 ? 'up' : change < 0 ? 'down' : ''
}

const formatChange = (change) => {
  if (change === null || change === undefined) return '--'
  const sign = change > 0 ? '+' : ''
  return `${sign}${change}%`
}

const formatNav = (nav) => {
  if (nav === null || nav === undefined) return '--'
  return nav
}
</script>

<style scoped>
.container {
  padding: 20px;
  background-color: #0d1117;
  min-height: 100vh;
  color: #c9d1d9;
}

/* 搜索栏 */
.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  height: 40px;
  padding: 0 15px;
  background: #21262d;
  border-radius: 8px;
  border: 1px solid #30363d;
  font-size: 14px;
  color: #c9d1d9;
}

.search-input::placeholder {
  color: #8b949e;
}

.search-btn {
  width: 80px;
  height: 40px;
  background: #238636;
  color: #fff;
  border-radius: 8px;
  border: none;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.search-btn:hover {
  background: #2ea043;
}

/* 市场概览 */
.market-overview {
  background: #161b22;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid #30363d;
}

.overview-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 15px;
  color: #f0f6fc;
}

.overview-stats {
  display: flex;
  gap: 40px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 28px;
  font-weight: bold;
  color: #f0f6fc;
}

.stat-value.up {
  color: #ff7b72;
}

.stat-value.down {
  color: #7ee787;
}

.stat-label {
  font-size: 12px;
  color: #8b949e;
  margin-top: 4px;
}

/* 基金列表 */
.fund-list {
  background: #161b22;
  border-radius: 12px;
  border: 1px solid #30363d;
  overflow: hidden;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #30363d;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #f0f6fc;
}

.filter-tabs {
  display: flex;
  gap: 8px;
}

.tab {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  color: #8b949e;
  transition: all 0.2s;
}

.tab:hover {
  background: #21262d;
  color: #c9d1d9;
}

.tab.active {
  background: #1f6feb;
  color: #fff;
}

/* 表格样式 */
.table-header {
  display: flex;
  padding: 12px 20px;
  background: #0d1117;
  border-bottom: 1px solid #30363d;
  font-size: 13px;
  font-weight: 600;
  color: #8b949e;
}

.table-body {
  max-height: 600px;
  overflow-y: auto;
}

.table-row {
  display: flex;
  padding: 14px 20px;
  border-bottom: 1px solid #21262d;
  align-items: center;
  transition: background 0.15s;
}

.table-row:hover {
  background: #1c2128;
}

.table-row:last-child {
  border-bottom: none;
}

.table-row.loading {
  opacity: 0.7;
}

.th, .td {
  padding: 0 8px;
}

.col-code {
  width: 80px;
  flex-shrink: 0;
}

.col-name {
  flex: 1;
  min-width: 150px;
}

.col-nav {
  width: 90px;
  text-align: right;
  flex-shrink: 0;
}

.col-change {
  width: 90px;
  text-align: right;
  flex-shrink: 0;
}

.col-time {
  width: 130px;
  text-align: center;
  flex-shrink: 0;
  color: #8b949e;
  font-size: 12px;
}

.col-status {
  width: 100px;
  text-align: center;
  flex-shrink: 0;
}

.col-actions {
  width: 100px;
  text-align: center;
  flex-shrink: 0;
}

.fund-name-text {
  color: #f0f6fc;
  font-weight: 500;
}

.nav-empty {
  color: #8b949e;
}

/* 涨跌幅颜色 */
.up {
  color: #ff7b72;
}

.down {
  color: #7ee787;
}

/* 状态标签 */
.status-tag {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.status-normal {
  background: #238636;
  color: #fff;
}

.status-nav {
  background: #1f6feb;
  color: #fff;
}

.status-loading {
  background: #9e8c6c;
  color: #fff;
  animation: pulse 1.5s infinite;
}

.status-error {
  background: #da3633;
  color: #fff;
}

.status-other {
  background: #6e7681;
  color: #fff;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.source-tag {
  display: block;
  font-size: 10px;
  color: #8b949e;
  margin-top: 2px;
}

/* 操作按钮 - 更小更紧凑 */
.action-btns {
  display: flex;
  gap: 6px;
  justify-content: center;
}

.icon-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  padding: 0;
}

.icon-btn:hover {
  transform: scale(1.1);
}

.icon-btn.detail {
  background: #21262d;
  color: #58a6ff;
  border: 1px solid #30363d;
}

.icon-btn.detail:hover {
  background: #1f6feb;
  color: #fff;
}

.icon-btn.add {
  background: #238636;
  color: #fff;
}

.icon-btn.add:hover {
  background: #2ea043;
}

.icon-btn.delete {
  background: #21262d;
  color: #f85149;
  border: 1px solid #30363d;
}

.icon-btn.delete:hover {
  background: #da3633;
  color: #fff;
}

/* 弹窗 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 400px;
  background: #161b22;
  border-radius: 12px;
  border: 1px solid #30363d;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #30363d;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: #f0f6fc;
}

.modal-close {
  font-size: 24px;
  color: #8b949e;
  cursor: pointer;
}

.modal-close:hover {
  color: #f0f6fc;
}

.modal-body {
  padding: 20px;
}

.fund-input {
  width: 100%;
  height: 44px;
  padding: 0 12px;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 8px;
  font-size: 14px;
  color: #c9d1d9;
  margin-bottom: 16px;
  box-sizing: border-box;
}

.fund-input:focus {
  outline: none;
  border-color: #1f6feb;
}

.confirm-btn {
  width: 100%;
  height: 44px;
  background: #238636;
  color: #fff;
  border-radius: 8px;
  border: none;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
}

.confirm-btn:hover {
  background: #2ea043;
}
</style>
