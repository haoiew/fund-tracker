/**
 * 持仓数据流测试工具
 * 用于验证从API到表格的数据流
 */

import { usePortfolioStore } from '@/stores/portfolioStore'

export async function testPortfolioDataFlow() {
  console.log('='.repeat(60))
  console.log('开始测试持仓数据流')
  console.log('='.repeat(60))

  const store = usePortfolioStore()

  // 测试1: 初始状态
  console.log('\n[测试1] 初始状态检查')
  console.log('-'.repeat(60))
  console.log('items:', store.items)
  console.log('items长度:', store.items.length)
  console.log('stats:', store.stats)
  console.log('loading:', store.loading)
  console.log('error:', store.error)
  console.log('initialized:', store.initialized)

  // 测试2: 获取数据
  console.log('\n[测试2] 调用 fetchPortfolio()')
  console.log('-'.repeat(60))

  try {
    await store.fetchPortfolio()

    console.log('fetchPortfolio 完成')
    console.log('items:', store.items)
    console.log('items长度:', store.items.length)
    console.log('items类型:', typeof store.items)
    console.log('Array.isArray(items):', Array.isArray(store.items))
    console.log('stats:', store.stats)
    console.log('loading:', store.loading)
    console.log('error:', store.error)

    // 测试3: 验证数据格式
    console.log('\n[测试3] 数据格式验证')
    console.log('-'.repeat(60))

    if (store.items.length > 0) {
      const firstItem = store.items[0]
      console.log('第一条数据:', firstItem)

      const requiredFields = [
        'id',
        'fund_code',
        'fund_name',
        'hold_shares',
        'cost_nav',
        'current_nav',
        'current_value',
        'profit_amount',
        'profit_rate'
      ]

      requiredFields.forEach(field => {
        if (field in firstItem) {
          console.log(`✅ ${field}: ${firstItem[field as keyof typeof firstItem]}`)
        } else {
          console.log(`❌ ${field}: 缺失`)
        }
      })
    } else {
      console.log('⚠️ items为空数组，无法验证数据格式')
    }

    // 测试4: 验证计算属性
    console.log('\n[测试4] 计算属性验证')
    console.log('-'.repeat(60))
    console.log('itemCount:', store.itemCount)
    console.log('totalValue:', store.totalValue)
    console.log('totalProfit:', store.totalProfit)
    console.log('totalProfitPct:', store.totalProfitPct)
    console.log('profitPositive:', store.profitPositive)
    console.log('hasData:', store.hasData)

    console.log('\n' + '='.repeat(60))
    console.log('测试完成')
    console.log('='.repeat(60))

    return {
      success: true,
      itemCount: store.items.length,
      stats: store.stats,
      error: null
    }
  } catch (e) {
    console.error('测试失败:', e)
    return {
      success: false,
      itemCount: 0,
      stats: null,
      error: e instanceof Error ? e.message : '未知错误'
    }
  }
}

// 在控制台运行的辅助函数
export function runPortfolioTest() {
  testPortfolioDataFlow().then(result => {
    console.log('\n测试结果:', result)
  })
}
