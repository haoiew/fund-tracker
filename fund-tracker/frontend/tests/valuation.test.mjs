import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createJiti } from 'jiti'

const jiti = createJiti(import.meta.url)
const { calculateDailyChange, isOfficialNavDisplayed, summarizePortfolioDay, withoutPortfolioQuote } = await jiti.import('../src/utils/portfolioValuation.ts')
const { deriveEstimateNav } = await jiti.import('../src/utils/fundEstimate.ts')
const now = new Date('2026-10-13T06:30:00Z')

test('daily return uses previous value, not current value times percent', () => {
  assert.ok(Math.abs(calculateDailyChange(110, 10) - 10) < 1e-10)
  const stats = summarizePortfolioDay([{ hold_shares: 100, current_value: 110, current_change: 10, quote_as_of: '2026-10-13 14:29' }], 'selected', now)
  assert.ok(Math.abs(stats.changeAmount - 10) < 1e-10)
  assert.ok(Math.abs(stats.changePct - 10) < 1e-10)
})

test('missing or previous-day quotes cannot become zero-profit totals', () => {
  assert.equal(calculateDailyChange(null, 0), null)
  assert.equal(calculateDailyChange(100, null), null)
  for (const quote of [null, '2026-10-12 14:29']) {
    assert.equal(summarizePortfolioDay([{ hold_shares: 100, current_value: 110, current_change: 10, quote_as_of: quote }], 'selected', now).changeAmount, null)
  }
})

test('zero-share holdings do not require a quote', () => {
  assert.deepEqual(summarizePortfolioDay([{ hold_shares: 0, current_value: null }], 'selected', now), { changeAmount: 0, changePct: 0 })
})

test('official NAV is automatic only after close and today publication, or manual selection', () => {
  assert.equal(isOfficialNavDisplayed({ official_update_time: '2026-10-13' }, now), false)
  assert.equal(isOfficialNavDisplayed({ official_update_time: '2026-10-13' }, new Date('2026-10-13T10:00:00Z')), true)
  assert.equal(isOfficialNavDisplayed({ official_update_time: '2026-10-12' }, new Date('2026-10-13T10:00:00Z')), false)
  assert.equal(isOfficialNavDisplayed({ data_kind: 'latest_nav', official_update_time: '2026-10-12' }, now), true)
})

test('latest NAV is a baseline, its previous-day change is not undone', () => {
  assert.equal(deriveEstimateNav({ data_kind: 'latest_nav', estimate_nav: 1.6, estimate_change: -0.85 }, 2.5), 1.64)
  assert.equal(deriveEstimateNav({ data_kind: 'unavailable', official_nav: 1.6, estimate_nav: null }, 2.5), 1.64)
})

test('unverified cached prices are removed without discarding holding inputs', () => {
  const row = withoutPortfolioQuote({ id: 1, fund_code: '161725', hold_shares: 100, cost_amount: 50, cost_nav: 0.5, current_value: 224.99, current_nav: 2.2499, quote_as_of: '2026-10-12' })
  assert.equal(row.hold_shares, 100)
  assert.equal(row.cost_amount, 50)
  assert.equal(row.cost_nav, 0.5)
  assert.equal(row.current_value, null)
  assert.equal(row.current_nav, null)
  assert.equal(row.quote_as_of, null)
  assert.equal(withoutPortfolioQuote({ hold_shares: 0 }).current_value, 0)
})
