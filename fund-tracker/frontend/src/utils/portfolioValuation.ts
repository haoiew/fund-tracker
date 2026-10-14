import type { PortfolioItem } from '@/api/portfolio'

// 保留账户输入，仅移除未经当前版本验证的报价及其衍生统计。
export const withoutPortfolioQuote = (item: PortfolioItem): PortfolioItem => ({
  ...item,
  current_nav: null, current_change: null,
  current_value: Number(item.hold_shares) === 0 ? 0 : null,
  profit_amount: null, profit_rate: null, daily_profit: null,
  realtime_change_pct: null, realtime_change_amount: null,
  official_nav: null, official_change_pct: null, official_change_amount: null,
  official_value: null, official_update_time: null,
  data_kind: 'unavailable', data_kind_label: '暂无可用估值',
  is_realtime: false, is_inferred: false, quote_as_of: null,
})

type DailyHolding = {
  hold_shares: number
  current_value?: number | null
  current_change?: number | null
  realtime_change_amount?: number | null
  daily_profit?: number | null
  quote_as_of?: string | null
  data_kind?: string | null
  official_nav?: number | null
  official_value?: number | null
  official_change_pct?: number | null
  official_update_time?: string | null
}

export const shanghaiDate = (now = new Date()): string =>
  now.toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' })

export const isOfficialNavDisplayed = (item: Pick<DailyHolding, 'data_kind' | 'official_update_time'>, now = new Date()): boolean => {
  const hour = Number(new Intl.DateTimeFormat('en', { timeZone: 'Asia/Shanghai', hour: 'numeric', hourCycle: 'h23' }).format(now))
  return item.data_kind === 'latest_nav' || (hour >= 15 && item.official_update_time === shanghaiDate(now))
}

export const calculateDailyChange = (value: number | null | undefined, pct: number | null | undefined): number | null => {
  if (value == null || pct == null || !Number.isFinite(Number(value)) || !Number.isFinite(Number(pct)) || Number(pct) <= -100) return null
  return Number(value) - Number(value) / (1 + Number(pct) / 100)
}

// 首页和持仓页共用同一日收益基准：以前一日价值为分母；缺项时不输出部分合计。
export const summarizePortfolioDay = (items: DailyHolding[], basis: 'selected' | 'official' = 'selected', now = new Date()) => {
  let value = 0
  let change = 0
  const unavailable = { changeAmount: null, changePct: null }
  for (const item of items) {
    if (Number(item.hold_shares) === 0) continue
    const isOfficial = basis === 'official'
    if (isOfficial ? !isOfficialNavDisplayed(item, now) : item.quote_as_of?.slice(0, 10) !== shanghaiDate(now)) return unavailable
    const currentValue = isOfficial
      ? item.official_value ?? (item.official_nav == null ? null : Number(item.official_nav) * Number(item.hold_shares))
      : item.current_value
    const contribution = isOfficial
      ? calculateDailyChange(currentValue, item.official_change_pct)
      : item.realtime_change_amount ?? item.daily_profit ?? calculateDailyChange(currentValue, item.current_change)
    if (currentValue == null || contribution == null || !Number.isFinite(Number(currentValue)) || !Number.isFinite(Number(contribution))) return unavailable
    value += Number(currentValue)
    change += Number(contribution)
  }
  return { changeAmount: change, changePct: value - change > 0 ? change / (value - change) * 100 : 0 }
}
