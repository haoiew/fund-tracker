<template>
  <view class="container">
    <!-- 资产总览 -->
    <view class="asset-overview" v-if="profitSummary">
      <view class="overview-header">
        <text class="header-title">资产总览</text>
        <text class="update-time">{{updateTime}}</text>
      </view>
      
      <view class="asset-grid">
        <view class="asset-item">
          <text class="asset-label">总市值</text>
          <text class="asset-value">¥{{formatMoney(totalValue)}}</text>
        </view>
        <view class="asset-item">
          <text class="asset-label">总投入</text>
          <text class="asset-value">¥{{formatMoney(totalCost)}}</text>
        </view>
        <view class="asset-item">
          <text class="asset-label">累计盈亏</text>
          <text class="asset-value" :class="totalProfit >= 0 ? 'up' : 'down'">
            {{totalProfit >= 0 ? '+' : ''}}¥{{formatMoney(totalProfit)}}
          </text>
        </view>
        <view class="asset-item">
          <text class="asset-label">收益率</text>
          <text class="asset-value" :class="profitRate >= 0 ? 'up' : 'down'">
            {{profitRate >= 0 ? '+' : ''}}{{profitRate.toFixed(2)}}%
          </text>
        </view>
      </view>
    </view>
    
    <!-- OCR导入 -->
    <view class="ocr-section">
      <button class="ocr-btn" @click="handleImageUpload">
        <text class="ocr-icon">📷</text>
        <text class="ocr-text">导入持仓截图</text>
      </button>
      <text class="ocr-tip">支持识别天天基金、支付宝等持仓截图</text>
    </view>

    <!-- 持仓列表 -->
    <view class="portfolio-list">
      <view class="list-header">
        <text class="header-title">我的持仓</text>
        <button class="add-btn" @click="showAddModal = true">+ 添加持仓</button>
      </view>
      
      <view 
        class="portfolio-item" 
        v-for="item in portfolios" 
        :key="item.id"
      >
        <view class="portfolio-header">
          <view class="fund-info">
            <text class="fund-name">{{item.fund_name}}</text>
            <text class="fund-code">{{item.fund_code}}</text>
          </view>
          <view class="profit-info">
            <text class="profit-amount" :class="item.profit_amount >= 0 ? 'up' : 'down'">
              {{item.profit_amount >= 0 ? '+' : ''}}¥{{formatMoney(item.profit_amount || 0)}}
            </text>
            <text class="profit-rate" :class="item.profit_rate >= 0 ? 'up' : 'down'">
              {{item.profit_rate >= 0 ? '+' : ''}}{{(item.profit_rate || 0).toFixed(2)}}%
            </text>
          </view>
        </view>
        
        <view class="portfolio-detail">
          <view class="detail-row">
            <text class="detail-label">持有份额</text>
            <text class="detail-value">{{item.hold_shares}}</text>
          </view>
          <view class="detail-row">
            <text class="detail-label">成本金额</text>
            <text class="detail-value">¥{{formatMoney(item.cost_amount)}}</text>
          </view>
          <view class="detail-row">
            <text class="detail-label">当前市值</text>
            <text class="detail-value">¥{{formatMoney(item.current_value || 0)}}</text>
          </view>
          <view class="detail-row">
            <text class="detail-label">今日涨跌</text>
            <text class="detail-value" :class="item.current_change >= 0 ? 'up' : 'down'">
              {{item.current_change >= 0 ? '+' : ''}}{{item.current_change || 0}}%
            </text>
          </view>
        </view>
        
        <view class="portfolio-actions">
          <button class="action-btn edit" @click="editPortfolio(item)">编辑</button>
          <button class="action-btn delete" @click="deletePortfolio(item.id)">删除</button>
        </view>
      </view>
    </view>
    
    <!-- 添加持仓弹窗 -->
    <view class="modal" v-if="showAddModal" @click="showAddModal = false">
      <view class="modal-content" @click.stop>
        <view class="modal-header">
          <text class="modal-title">添加持仓</text>
          <text class="modal-close" @click="showAddModal = false">×</text>
        </view>
        <view class="modal-body">
          <input class="input" placeholder="基金代码" v-model="form.fund_code" />
          <input class="input" placeholder="持有份额" type="digit" v-model="form.hold_shares" />
          <input class="input" placeholder="投入金额" type="digit" v-model="form.cost_amount" />
          <button class="confirm-btn" @click="submitPortfolio">确认</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { usePortfolioStore } from '../../stores/portfolioStore.js'
import { ocrApi } from '../../api/ocr.js'

const portfolioStore = usePortfolioStore()
const showAddModal = ref(false)
const updateTime = ref(new Date().toLocaleString())
const ocrLoading = ref(false)

const form = ref({
  fund_code: '',
  hold_shares: '',
  cost_amount: ''
})

const portfolios = computed(() => portfolioStore.portfolios)
const profitSummary = computed(() => portfolioStore.profitSummary)
const totalCost = computed(() => portfolioStore.totalCost)
const totalValue = computed(() => portfolioStore.totalValue)
const totalProfit = computed(() => portfolioStore.totalProfit)
const profitRate = computed(() => portfolioStore.profitRate)

onMounted(() => {
  loadData()
})

const loadData = async () => {
  await portfolioStore.fetchPortfolios()
  await portfolioStore.fetchProfit()
  updateTime.value = new Date().toLocaleString()
}

const submitPortfolio = async () => {
  const data = {
    fund_code: form.value.fund_code,
    hold_shares: parseFloat(form.value.hold_shares),
    cost_amount: parseFloat(form.value.cost_amount)
  }
  
  const success = await portfolioStore.addPortfolio(data)
  if (success) {
    showAddModal.value = false
    form.value = { fund_code: '', hold_shares: '', cost_amount: '' }
    uni.showToast({ title: '添加成功', icon: 'success' })
  }
}

const deletePortfolio = async (id) => {
  uni.showModal({
    title: '确认删除',
    content: '确定要删除这个持仓吗？',
    success: async (res) => {
      if (res.confirm) {
        const success = await portfolioStore.deletePortfolio(id)
        if (success) {
          uni.showToast({ title: '删除成功', icon: 'success' })
        }
      }
    }
  })
}

const formatMoney = (value) => {
  if (!value) return '0.00'
  return parseFloat(value).toFixed(2)
}

// OCR图片上传和识别
const handleImageUpload = () => {
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed'],
    sourceType: ['album', 'camera'],
    success: (res) => {
      const tempFilePath = res.tempFilePaths[0]
      processOCR(tempFilePath)
    },
    fail: (err) => {
      console.error('选择图片失败:', err)
      uni.showToast({ title: '选择图片失败', icon: 'none' })
    }
  })
}

// 处理OCR识别
const processOCR = async (filePath) => {
  ocrLoading.value = true
  uni.showLoading({ title: '识别中...' })

  try {
    // 读取图片并转换为base64
    const fs = uni.getFileSystemManager()
    const fileData = fs.readFileSync(filePath, 'base64')

    // 调用OCR API
    const result = await ocrApi.extractPositions(fileData)

    if (result.code === 200 && result.data) {
      const positions = result.data.positions || []

      if (positions.length === 0) {
        uni.showToast({ title: '未识别到持仓数据', icon: 'none' })
        return
      }

      // 导入识别到的持仓
      let successCount = 0
      let skipCount = 0
      
      for (const pos of positions) {
        if (pos.fund_code) {
          // 优先使用后端计算好的数据
          let holdShares = pos.hold_shares
          let costAmount = pos.cost_amount

          // 如果没有计算好的数据，尝试从市值和收益率估算
          if (!holdShares && pos.market_value && pos.profit_rate !== null) {
            const cost = pos.market_value / (1 + pos.profit_rate)
            costAmount = Math.round(cost * 100) / 100
            // 估算份额（假设净值约为1）
            holdShares = Math.round(cost * 100) / 100
          }

          if (holdShares && costAmount) {
            const data = {
              fund_code: pos.fund_code,
              hold_shares: parseFloat(holdShares),
              cost_amount: parseFloat(costAmount)
            }

            const success = await portfolioStore.addPortfolio(data)
            if (success) {
              successCount++
            } else {
              skipCount++
            }
          } else {
            skipCount++
          }
        } else {
          skipCount++
        }
      }

      let msg = `成功导入 ${successCount} 只基金`
      if (skipCount > 0) {
        msg += `，跳过 ${skipCount} 只`
      }
      
      uni.showToast({
        title: msg,
        icon: successCount > 0 ? 'success' : 'none'
      })

      // 刷新数据
      if (successCount > 0) {
        await loadData()
      }
    } else {
      uni.showToast({ title: result.message || '识别失败', icon: 'none' })
    }
  } catch (error) {
    console.error('OCR识别失败:', error)
    uni.showToast({ title: '识别失败: ' + error.message, icon: 'none' })
  } finally {
    ocrLoading.value = false
    uni.hideLoading()
  }
}
</script>

<style scoped>
.container {
  padding: 20rpx;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.asset-overview {
  background: linear-gradient(135deg, #1890ff, #36cfc9);
  border-radius: 20rpx;
  padding: 40rpx;
  margin-bottom: 20rpx;
  color: #fff;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30rpx;
}

.header-title {
  font-size: 32rpx;
  font-weight: bold;
}

.update-time {
  font-size: 24rpx;
  opacity: 0.8;
}

.asset-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30rpx;
}

.asset-item {
  text-align: center;
}

.asset-label {
  display: block;
  font-size: 24rpx;
  opacity: 0.9;
  margin-bottom: 10rpx;
}

.asset-value {
  display: block;
  font-size: 36rpx;
  font-weight: bold;
}

.asset-value.up {
  color: #ffccc7;
}

.asset-value.down {
  color: #d9f7be;
}

.portfolio-list {
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.add-btn {
  width: 160rpx;
  height: 60rpx;
  line-height: 60rpx;
  background: #1890ff;
  color: #fff;
  border-radius: 30rpx;
  font-size: 24rpx;
  padding: 0;
}

/* OCR导入区域 */
.ocr-section {
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
  text-align: center;
}

.ocr-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
  width: 100%;
  height: 100rpx;
  background: linear-gradient(135deg, #1890ff, #36cfc9);
  border-radius: 16rpx;
  border: none;
  margin-bottom: 16rpx;
}

.ocr-icon {
  font-size: 40rpx;
}

.ocr-text {
  font-size: 32rpx;
  color: #fff;
  font-weight: 500;
}

.ocr-tip {
  font-size: 24rpx;
  color: #999;
}

.portfolio-item {
  background: #fafafa;
  border-radius: 16rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
}

.portfolio-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20rpx;
  padding-bottom: 20rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.fund-name {
  display: block;
  font-size: 30rpx;
  font-weight: 500;
  color: #333;
}

.fund-code {
  font-size: 24rpx;
  color: #999;
}

.profit-info {
  text-align: right;
}

.profit-amount {
  display: block;
  font-size: 32rpx;
  font-weight: bold;
}

.profit-rate {
  font-size: 24rpx;
}

.up {
  color: #ff4d4f;
}

.down {
  color: #52c41a;
}

.portfolio-detail {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20rpx;
  margin-bottom: 20rpx;
}

.detail-row {
  display: flex;
  justify-content: space-between;
}

.detail-label {
  font-size: 24rpx;
  color: #999;
}

.detail-value {
  font-size: 26rpx;
  color: #333;
}

.portfolio-actions {
  display: flex;
  gap: 20rpx;
}

.action-btn {
  flex: 1;
  height: 60rpx;
  line-height: 60rpx;
  border-radius: 30rpx;
  font-size: 24rpx;
  padding: 0;
}

.action-btn.edit {
  background: #f0f0f0;
  color: #666;
}

.action-btn.delete {
  background: #fff1f0;
  color: #ff4d4f;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 80%;
  background: #fff;
  border-radius: 20rpx;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.modal-title {
  font-size: 32rpx;
  font-weight: bold;
}

.modal-close {
  font-size: 40rpx;
  color: #999;
}

.modal-body {
  padding: 40rpx 30rpx;
}

.input {
  width: 100%;
  height: 80rpx;
  padding: 0 20rpx;
  border: 2rpx solid #d9d9d9;
  border-radius: 10rpx;
  font-size: 28rpx;
  margin-bottom: 20rpx;
  box-sizing: border-box;
}

.confirm-btn {
  width: 100%;
  height: 80rpx;
  line-height: 80rpx;
  background: #1890ff;
  color: #fff;
  border-radius: 10rpx;
  font-size: 30rpx;
}
</style>
