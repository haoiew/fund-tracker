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
    getRealtimeBatch: async (codes, view, refresh) => {
      calls.push([view, [...codes], refresh])
      if (view === 'provider') return codes.map(providerRow)
      reachedInference()
      return inference
    }
  })
  const loading = manager.initialize()
  // Old startup finishes before its network work; it must fail rather than hang this test.
  await Promise.race([reached, loading])
  assert.equal(manager.getRealtimeData('012349')?.estimate_nav, 1.2)
  await loading
  assert.equal(manager.getState().realtimeLoading, false)
  assert.equal(manager.getState().realtimeSourcesLoading, true)
  releaseInference([{ ...providerRow('015916'), estimate_nav: 1.05, data_kind: 'holdings_estimate', is_inferred: true }])
  await new Promise(resolve => setImmediate(resolve))
  assert.deepEqual(calls, [['holdings', false], ['provider', ['012349', '015916'], true], ['auto', ['015916'], false]])
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
  await new Promise(resolve => setImmediate(resolve))
  assert.match(manager.getState().realtimeError, /后台补充.*请求超时/)
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

test('each startup and explicit refresh bypass quote caches, auto only reuses the same snapshot', async () => {
  const calls = []
  const manager = await setup({
    getFundList: async () => ['012349'],
    getAll: async () => ({ items: [position], stats }),
    getRealtimeBatch: async (codes, view, refresh) => { calls.push([view, refresh]); return codes.map(providerRow) }
  })
  await manager.initialize()
  await manager.initialize() // A fresh localStorage quote must not suppress startup's network refresh.
  await manager.refreshAll()
  assert.deepEqual(calls, [['provider', true], ['auto', false], ['provider', true], ['auto', false], ['provider', true], ['auto', false]])
})


test('primary failure ends main loading while backups later fill the list without another forced fetch', async () => {
  const calls = []
  let releaseBackup, reachedPoll
  const backup = new Promise(resolve => { releaseBackup = resolve })
  const polled = new Promise(resolve => { reachedPoll = resolve })
  const missing = { ...providerRow('015916'), primary_source_complete: true, pending_sources: ['dayfund', 'fund123'] }
  const manager = await setup({
    getFundList: async () => [],
    getAll: async () => ({ items: [position], stats }),
    getRealtimeBatch: async (codes, view, refresh) => {
      calls.push([view, refresh])
      if (refresh) return [missing]
      reachedPoll()
      return backup
    }
  }, [])
  await manager.initialize()
  assert.equal(manager.getState().realtimeLoading, false)
  assert.equal(manager.getState().realtimeSourcesLoading, true)
  assert.equal(manager.getRealtimeData('015916').estimate_nav, null)
  await polled
  releaseBackup([{ ...missing, estimate_nav: 1.1, is_realtime: true, data_source: 'dayfund', data_kind: 'realtime_estimate', pending_sources: [] }])
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(manager.getRealtimeData('015916').estimate_nav, 1.1)
  assert.equal(manager.getState().realtimeSourcesLoading, false)
  assert.deepEqual(calls, [['provider', true], ['provider', false]])
})

test('a faster backup is visible before primary completion and never overrides a valid primary later', async () => {
  let releasePrimary, reachedPoll
  const primary = new Promise(resolve => { releasePrimary = resolve })
  const polled = new Promise(resolve => { reachedPoll = resolve })
  const first = { ...providerRow('012349'), data_source: 'tiantian', primary_source_complete: false, pending_sources: ['sina'] }
  const manager = await setup({
    getFundList: async () => ['012349'], getAll: async () => ({ items: [], stats }),
    getRealtimeBatch: async (codes, view, refresh) => {
      if (refresh) return [first]
      reachedPoll()
      return primary
    }
  })
  const loading = manager.initialize()
  await polled
  assert.equal(manager.getRealtimeData('012349').data_source, 'tiantian')
  assert.equal(manager.getState().realtimeLoading, true)
  releasePrimary([{ ...first, data_source: 'sina', primary_source_complete: true, pending_sources: [] }])
  await loading
  assert.equal(manager.getRealtimeData('012349').data_source, 'sina')
  assert.equal(manager.getState().realtimeLoading, false)
})


test('late inference from an older refresh cannot overwrite a newer provider quote', async () => {
  let releaseInference
  const inference = new Promise(resolve => { releaseInference = resolve })
  let rounds = 0
  const manager = await setup({
    getFundList: async () => [], getAll: async () => ({ items: [position], stats }),
    getRealtimeBatch: async (codes, view, refresh) => {
      if (view === 'auto') return inference
      if (refresh) rounds++
      return [{ ...providerRow('015916'), estimate_nav: rounds > 1 ? 1.15 : null, data_kind: rounds > 1 ? 'realtime_estimate' : 'unavailable', is_realtime: rounds > 1, pending_sources: [], primary_source_complete: true }]
    }
  }, [])
  await manager.initialize()
  await manager.refreshAll()
  releaseInference([{ ...providerRow('015916'), estimate_nav: 1.05, data_kind: 'holdings_estimate', is_inferred: true }])
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(manager.getRealtimeData('015916').estimate_nav, 1.15)
  assert.equal(manager.getRealtimeData('015916').data_kind, 'realtime_estimate')
})


test('manual NAV selection survives background completion and next refresh restores priority', async () => {
  let releaseBackup, reachedPoll
  const backup = new Promise(resolve => { releaseBackup = resolve })
  const polled = new Promise(resolve => { reachedPoll = resolve })
  let rounds = 0
  const source = { ...providerRow('012349'), data_source: 'sina', is_realtime: true, primary_source_complete: true }
  const manager = await setup({
    getFundList: async () => ['012349'], getAll: async () => ({ items: [], stats }),
    getRealtimeBatch: async (codes, view, refresh) => {
      if (refresh) return [{ ...source, estimate_nav: ++rounds === 1 ? 1.2 : 1.25, pending_sources: rounds === 1 ? ['fund123'] : [] }]
      reachedPoll()
      return backup
    }
  })
  await manager.initialize()
  manager.updateRealtimeItem({ ...source, estimate_nav: .95, data_source: 'tiantian', data_kind: 'latest_nav', is_realtime: false, update_time: '2026-10-13' }, true)
  await polled
  releaseBackup([{ ...source, estimate_nav: 1.22, pending_sources: [] }])
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(manager.getRealtimeData('012349').estimate_nav, .95)
  assert.equal(manager.getRealtimeData('012349').data_kind, 'latest_nav')
  assert.deepEqual(manager.getRealtimeData('012349').pending_sources, [])
  await manager.refreshAll()
  assert.equal(manager.getRealtimeData('012349').estimate_nav, 1.25)
  assert.equal(manager.getRealtimeData('012349').data_source, 'sina')
})
