import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createJiti } from 'jiti'

const { exportFundsToCSV, exportPortfolioToCSV } = await createJiti(import.meta.url).import('../src/utils/export.ts')

test('exports Decimal strings, zero changes and unknown prices without coercing fund codes', async () => {
  const blobs = []
  const originalDocument = globalThis.document
  const originalCreate = URL.createObjectURL
  const originalRevoke = URL.revokeObjectURL
  globalThis.document = {
    createElement: () => ({ click() {} }),
    body: { appendChild() {}, removeChild() {} },
  }
  URL.createObjectURL = blob => { blobs.push(blob); return 'blob:test' }
  URL.revokeObjectURL = () => {}
  try {
    exportFundsToCSV([{ code: '012414', name: '测试基金', estimate_nav: '0.5289', estimate_change: '0', update_time: '2026-10-14 09:48', status: '实时估值' }])
    exportPortfolioToCSV([{ fund_code: '012414', hold_shares: '100', cost_nav: '0.5000', current_nav: null, current_value: null, profit_amount: null, profit_rate: null }])
    const fundCSV = await blobs[0].text()
    const portfolioCSV = await blobs[1].text()
    assert.ok(fundCSV.includes('012414,测试基金,0.5289,0.00%'))
    assert.ok(portfolioCSV.includes('012414,,100.00,0.5000,--,--,--,--'))
  } finally {
    if (originalDocument === undefined) delete globalThis.document
    else globalThis.document = originalDocument
    URL.createObjectURL = originalCreate
    URL.revokeObjectURL = originalRevoke
  }
})
