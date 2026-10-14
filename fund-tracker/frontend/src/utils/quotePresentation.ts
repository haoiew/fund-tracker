// Presentation only: price kinds and detailed inference provenance stay unchanged.
type QuoteDisplayInput = {
  estimate_nav?: number | string | null
  current_nav?: number | null
  data_kind?: string | null
  is_realtime?: boolean
  is_inferred?: boolean
  error?: string | null
  status?: string
}

type QuoteBadge = { label: string, type: 'primary' | 'success' | 'warning' | 'danger' }
const inferredKinds = new Set(['holdings_estimate', 'reference_symbol_estimate', 'similar_realtime_reference', 'fallback_estimate'])

export function getQuoteBadge(quote: QuoteDisplayInput): QuoteBadge {
  const nav = Number(quote.estimate_nav ?? quote.current_nav)
  if (!Number.isFinite(nav) || nav <= 0) {
    return quote.error ? { label: '异常', type: 'danger' } : { label: '无估值', type: 'warning' }
  }
  if (quote.is_inferred || inferredKinds.has(quote.data_kind || '')) return { label: '推算', type: 'primary' }
  if (quote.data_kind === 'latest_nav') return { label: '净值', type: 'success' }
  if (quote.data_kind === 'realtime_estimate' && quote.is_realtime === false) return { label: '过期', type: 'warning' }
  return { label: '正常', type: 'success' }
}

export function formatQuoteTime(timestamp?: string | null): string {
  if (!timestamp || timestamp === '--') return '--'
  if (/^\d{4}-\d{2}-\d{2}$/.test(timestamp)) return timestamp.slice(5)
  let iso = timestamp.trim().replace(' ', 'T')
  if (!/(Z|[+-]\d{2}:\d{2})$/i.test(iso)) iso += '+08:00'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '--'
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
  }).formatToParts(date)
  const part = (key: Intl.DateTimeFormatPartTypes) => parts.find(item => item.type === key)?.value
  return `${part('month')}-${part('day')} ${part('hour')}:${part('minute')}`
}
