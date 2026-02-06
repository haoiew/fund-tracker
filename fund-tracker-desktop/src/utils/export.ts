import type { FundRealtimeData } from '@/api/fund'
import type { PortfolioItem } from '@/api/portfolio'

/**
 * 导出数据为CSV格式
 */
export function exportToCSV(data: Record<string, unknown>[], filename: string): void {
  if (data.length === 0 || !data[0]) {
    console.warn('没有数据可导出')
    return
  }

  // 获取表头
  const headers = Object.keys(data[0])

  // 创建CSV内容
  const csvContent = [
    // 表头
    headers.join(','),
    // 数据行
    ...data.map(row =>
      headers.map(header => {
        const value = row[header]
        // 处理包含逗号或引号的值
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`
        }
        return value ?? ''
      }).join(',')
    )
  ].join('\n')

  // 添加BOM以支持中文
  const BOM = '\uFEFF'
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })

  // 创建下载链接
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${filename}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}

/**
 * 导出基金数据为CSV
 */
export function exportFundsToCSV(funds: FundRealtimeData[]): void {
  const data = funds.map(fund => ({
    '基金代码': fund.code,
    '基金名称': fund.name,
    '估算净值': fund.estimate_nav ?? '--',
    '涨跌幅': fund.estimate_change ? `${fund.estimate_change > 0 ? '+' : ''}${fund.estimate_change.toFixed(2)}%` : '--',
    '更新时间': fund.update_time,
    '状态': fund.status
  }))

  const timestamp = new Date().toISOString().slice(0, 10)
  exportToCSV(data, `基金数据_${timestamp}`)
}

/**
 * 导出持仓数据为CSV
 */
export function exportPortfolioToCSV(items: PortfolioItem[]): void {
  const data = items.map(item => ({
    '基金代码': item.fund_code,
    '基金名称': item.fund_name,
    '持有份额': item.hold_shares?.toFixed(2) ?? '--',
    '成本价': item.cost_nav?.toFixed(4) ?? '--',
    '当前净值': item.current_nav?.toFixed(4) ?? '--',
    '当前市值': item.current_value?.toFixed(2) ?? '--',
    '盈亏金额': item.profit_amount?.toFixed(2) ?? '--',
    '盈亏比例': item.profit_rate ? `${item.profit_rate > 0 ? '+' : ''}${item.profit_rate.toFixed(2)}%` : '--'
  }))

  const timestamp = new Date().toISOString().slice(0, 10)
  exportToCSV(data, `持仓数据_${timestamp}`)
}

/**
 * 导出数据为JSON格式
 */
export function exportToJSON(data: unknown, filename: string): void {
  const jsonContent = JSON.stringify(data, null, 2)
  const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' })

  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${filename}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}

/**
 * 复制文本到剪贴板
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return success
  }
}
