// 持仓相关API
import request from './request.js'

export const portfolioApi = {
  // 获取持仓列表
  getList() {
    return request({
      url: '/portfolio',
      method: 'GET'
    })
  },
  
  // 添加持仓
  add(data) {
    return request({
      url: '/portfolio',
      method: 'POST',
      data
    })
  },
  
  // 更新持仓
  update(id, data) {
    return request({
      url: `/portfolio/${id}`,
      method: 'PUT',
      data
    })
  },
  
  // 删除持仓
  delete(id) {
    return request({
      url: `/portfolio/${id}`,
      method: 'DELETE'
    })
  },
  
  // 获取收益统计
  getProfit() {
    return request({
      url: '/portfolio/profit',
      method: 'GET'
    })
  }
}
