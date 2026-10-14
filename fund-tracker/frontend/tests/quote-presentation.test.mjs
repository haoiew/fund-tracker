import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createJiti } from 'jiti'

const jiti = createJiti(import.meta.url)
const { getQuoteBadge, formatQuoteTime } = await jiti.import('../src/utils/quotePresentation.ts')

test('valid inferred quotes use a short blue badge, not the gray default', () => {
  for (const kind of ['holdings_estimate', 'reference_symbol_estimate', 'similar_realtime_reference']) {
    const badge = getQuoteBadge({ estimate_nav: 1.5555, data_kind: kind, is_inferred: true, status: '披露持仓外推' })
    assert.equal(badge.label, '推算')
    assert.equal(badge.type, 'primary')
  }
})

test('provider, official NAV, missing prices and failures remain distinct', () => {
  assert.deepEqual(getQuoteBadge({ estimate_nav: 0.5266, data_kind: 'realtime_estimate', is_realtime: true }), { label: '正常', type: 'success' })
  assert.deepEqual(getQuoteBadge({ estimate_nav: 1.5845, data_kind: 'latest_nav' }), { label: '净值', type: 'success' })
  assert.deepEqual(getQuoteBadge({ estimate_nav: null, data_kind: 'unavailable', is_inferred: true }), { label: '无估值', type: 'warning' })
  assert.deepEqual(getQuoteBadge({ estimate_nav: null, error: 'upstream timeout' }), { label: '异常', type: 'danger' })
})

test('quote time is compact and consistent in Shanghai, without inventing a NAV publication hour', () => {
  assert.equal(formatQuoteTime('2026-10-14T11:59:59+08:00'), '10-14 11:59')
  assert.equal(formatQuoteTime('2026-10-14 11:30'), '10-14 11:30')
  assert.equal(formatQuoteTime('2026-10-14T03:59:59Z'), '10-14 11:59')
  assert.equal(formatQuoteTime('2026-10-13'), '10-13')
  assert.equal(formatQuoteTime('--'), '--')
  assert.equal(formatQuoteTime('not a timestamp'), '--')
})


test('a pending backup is blue and is not misreported as an upstream failure', () => {
  assert.deepEqual(getQuoteBadge({ estimate_nav: null, pending_sources: ['dayfund'], error: null }), { label: '补充中', type: 'primary' })
})
