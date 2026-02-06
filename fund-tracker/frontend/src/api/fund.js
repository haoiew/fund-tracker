// 基金相关API
import request from './request.js'

export const fundApi = {
  // 获取实时估值
  getRealtime(code) {
    return request({
      url: `/funds/realtime/${code}`,
      method: 'GET'
    })
  },
  
  // 批量获取实时估值
  getRealtimeBatch(codes) {
    return request({
      url: '/funds/realtime/batch',
      method: 'POST',
      data: codes
    })
  },
  
  // 获取历史数据
  getHistory(code, range = '3M') {
    return request({
      url: `/funds/${code}/history?range=${range}`,
      method: 'GET'
    })
  },
  
  // 搜索基金
  search(keyword, limit = 10) {
    return request({
      url: '/funds/search',
      method: 'POST',
      data: { keyword, limit }
    })
  },
  
  // 筛选上涨基金
  screenUp(codes, minDays = 2, minPct = 0.03) {
    return request({
      url: `/funds/screen/up?codes=${codes.join(',')}&min_days=${minDays}&min_pct=${minPct}`,
      method: 'GET'
    })
  },
  
  // 筛选下跌基金
  screenDown(codes, minDays = 3, minPct = 0.03) {
    return request({
      url: `/funds/screen/down?codes=${codes.join(',')}&min_days=${minDays}&min_pct=${minPct}`,
      method: 'GET'
    })
  },
  
  // 获取默认基金列表
  getDefaultList() {
    return request({
      url: '/funds/default-list',
      method: 'GET'
    })
  }
}
