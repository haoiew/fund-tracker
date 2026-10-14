import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createJiti } from 'jiti'
const jiti = createJiti(import.meta.url)
const { getQuoteQualityText } = await jiti.import('../src/utils/quotePresentation.ts')

test('quality text distinguishes serving source, NAV source and fetch/quote times without inventing currency', () => {
  const text = getQuoteQualityText({ price_basis: 'provider_estimate', currency: null, upstream_family: 'sina',
    source_time: '2026-10-14 14:00', fetched_at: '2026-10-14T14:05:00+08:00', nav_date: '2026-10-13', nav_source: 'tiantian',
    warnings: [{ code: 'provider_estimate', message: '平台估值非正式净值' }] })
  assert.match(text, /口径：平台估值/)
  assert.match(text, /币种未核实/)
  assert.match(text, /上游：sina/)
  assert.match(text, /源时刻：10-14 14:00/)
  assert.match(text, /获取时刻：10-14 14:05/)
  assert.match(text, /2026-10-13（tiantian）/)
  assert.match(text, /平台估值非正式净值/)
})

test('missing quality produces no fabricated label and unknown upstream stays unknown', () => {
  assert.equal(getQuoteQualityText(null), '')
  assert.equal(getQuoteQualityText(undefined), '')
  assert.match(getQuoteQualityText({ price_basis: 'unit_nav', currency: null, upstream_family: null,
    source_time: null, fetched_at: null, nav_date: null, warnings: [] }), /上游：未核实/)
})
