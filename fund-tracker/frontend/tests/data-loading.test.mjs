import { test } from 'node:test'
import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { createJiti } from 'jiti'

async function setup(api, watchlist = ['012349']) {
  const storage = new Map([
    ['fund_tracker_fund_list', JSON.stringify(watchlist)],
    ['fund_tracker_fund_list_dirty', 'true']
  ])
  globalThis.localStorage = {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: key => storage.delete(key)
  }
  globalThis.loadingTestApi = api
  const jiti = createJiti(import.meta.url, {
    moduleCache: false,
    alias: {
      '@/utils': fileURLToPath(new URL('../src/utils', import.meta.url)),
      '@/api/fund': fileURLToPath(new URL('./helpers/loading-api.mjs', import.meta.url)),
      '@/api/portfolio': fileURLToPath(new URL('./helpers/loading-api.mjs', import.meta.url))
    }
  })
  return (await jiti.import('../src/stores/dataManager.ts')).dataManager
}

const position = { id: 1, fund_code: '015916', hold_shares: 100, cost_amount: 150 }
const stats = { item_count: 1, total_cost: 150, total_value: null, total_profit_loss: null, total_profit_loss_pct: null }
const providerRow = code => ({ code, name: `基金${code}`, estimate_nav: code === '012349' ? 1.2 : null,
  estimate_change: code === '012349' ? 1 : null, data_kind: code === '012349' ? 'realtime_estimate' : 'unavailable',
  update_time: '2026-10-14 10:59', official_nav: 1, official_update_time: '2026-10-13' })

test('startup fetches local holdings once, displays providers before finishing inference', async () => {
  const calls = []
  let releaseInference
  const inference = new Promise(resolve => { releaseInference = resolve })
  let reachedInference
  const reached = new Promise(resolve => { reachedInference = resolve })
  const manager = await setup({
    getFundList: async () => ['012349'],
    getAll: async includeQuotes => { calls.push(['holdings', includeQuotes]); return { items: [position], stats } },
    getRealtimeBatch: async (codes, view) => {
      calls.push([view, [...codes]])
      if (view === 'provider') return codes.map(providerRow)
      reachedInference()
      return inference
    }
  })
  const loading = manager.initialize()
  // Old startup finishes before its network work; it must fail rather than hang this test.
  await Promise.race([reached, loading])
  assert.equal(manager.getRealtimeData('012349')?.estimate_nav, 1.2)
  assert.equal(manager.getState().realtimeLoading, true)
  releaseInference([{ ...providerRow('015916'), estimate_nav: 1.05, data_kind: 'holdings_estimate', is_inferred: true }])
  await loading
  assert.deepEqual(calls, [['holdings', false], ['provider', ['012349', '015916']], ['auto', ['015916']]])
  assert.equal(manager.getRealtimeData('015916').estimate_nav, 1.05)
  assert.equal(manager.getPortfolioWithRealtime.value[0].fund_name, '基金015916')
  assert.equal(manager.getState().realtimeLoading, false)
})

test('failure to supplement inference keeps real provider quotes and a useful error', async () => {
  const manager = await setup({
    getFundList: async () => ['012349'],
    getAll: async () => ({ items: [position], stats }),
    getRealtimeBatch: async (codes, view) => {
      if (view === 'provider') return codes.map(providerRow)
      throw new Error('请求超时')
    }
  })
  await manager.initialize()
  assert.equal(manager.getRealtimeData('012349')?.estimate_nav, 1.2)
  assert.equal(manager.getRealtimeData('015916')?.estimate_nav, null)
  assert.match(manager.getState().realtimeError, /推算.*请求超时/)
  assert.equal(manager.getState().realtimeLoading, false)
})

test('empty watchlist still loads portfolio quotes without inventing watchlist entries', async () => {
  const calls = []
  const manager = await setup({
    getFundList: async () => [],
    getAll: async () => ({ items: [position], stats }),
    getRealtimeBatch: async (codes, view) => { calls.push([view, [...codes]]); return codes.map(providerRow) }
  }, [])
  await manager.initialize()
  assert.deepEqual(manager.getFundList.value, [])
  assert.equal(manager.getPortfolioItems.value.length, 1)
  assert.equal(manager.getAllRealtimeData.value.length, 1)
  assert.deepEqual(calls, [['provider', ['015916']], ['auto', ['015916']]])
})
