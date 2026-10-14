import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createJiti } from 'jiti'

const jiti = createJiti(import.meta.url)
const { chooseApiBaseUrl, DEFAULT_NATIVE_API_BASE } = await jiti.import('../src/platform/apiDefaults.ts')

test('web development uses the proxy instead of a persisted native default', () => {
  assert.equal(chooseApiBaseUrl({ stored: DEFAULT_NATIVE_API_BASE, configured: '/api', dev: true }), '/api')
  assert.equal(chooseApiBaseUrl({ configured: '/api', dev: true }), '/api')
})

test('custom backend addresses and native defaults remain supported', () => {
  assert.equal(chooseApiBaseUrl({ stored: 'https://funds.example.test/api/v1', dev: true }), 'https://funds.example.test/api/v1')
  assert.equal(chooseApiBaseUrl({ isTauri: true }), DEFAULT_NATIVE_API_BASE)
  assert.equal(chooseApiBaseUrl({ isTauri: true, stored: DEFAULT_NATIVE_API_BASE, tauriConfigured: 'http://localhost:8002/api/v1' }), 'http://localhost:8002/api/v1')
  assert.equal(chooseApiBaseUrl({ configured: '/api/v1' }), '/api/v1')
})
