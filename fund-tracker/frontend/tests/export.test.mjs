import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createJiti } from 'jiti'

const { exportFundsToCSV, exportPortfolioToCSV, exportToJSON } = await createJiti(import.meta.url).import('../src/utils/export.ts')

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

test('Android exports use the document picker, preserve UTF-8 content and report cancellation', async () => {
  const originalWindow = globalThis.window
  const originalNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  const calls = []
  globalThis.window = {
    __TAURI__: {},
    __TAURI_INTERNALS__: { invoke: async (command, args) => {
      calls.push({ command, args })
      return { saved: calls.length === 1 }
    } },
  }
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { userAgent: 'Android Test WebView' } })
  try {
    assert.equal(await exportFundsToCSV([{ code: '000001', name: '测试', estimate_nav: null, estimate_change: null }]), true)
    assert.equal(await exportToJSON({ code: '000001' }, '备份'), false)
    assert.equal(calls[0].command, 'plugin:fund-backend|save_file')
    assert.equal(calls[0].args.file.mimeType, 'text/csv')
    assert.ok(calls[0].args.file.content.startsWith('\uFEFF'))
    assert.ok(calls[0].args.file.content.includes('000001,测试,--,--'))
    assert.equal(calls[1].args.file.filename, '备份.json')
  } finally {
    if (originalWindow === undefined) delete globalThis.window
    else globalThis.window = originalWindow
    if (originalNavigator) Object.defineProperty(globalThis, 'navigator', originalNavigator)
    else delete globalThis.navigator
  }
})
