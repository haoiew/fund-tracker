import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createJiti } from 'jiti'

const { setEmbeddedConnection, getEmbeddedApiBaseUrl, getEmbeddedAccessToken } =
  await createJiti(import.meta.url).import('../src/platform/embeddedConnection.ts')

test('embedded API connection accepts loopback only and never forwards its secret externally', () => {
  assert.throws(() => setEmbeddedConnection({ apiBaseUrl: 'https://example.com/api/v1', accessToken: 'test-token' }))
  assert.throws(() => setEmbeddedConnection({ apiBaseUrl: 'http://127.0.0.1:9000/api/v1', accessToken: '' }))
  const local = 'http://127.0.0.1:49152/api/v1'
  setEmbeddedConnection({ apiBaseUrl: local, accessToken: 'test-token' })
  assert.equal(getEmbeddedApiBaseUrl(), local)
  assert.equal(getEmbeddedAccessToken(local, '/portfolio'), 'test-token')
  assert.equal(getEmbeddedAccessToken('https://example.com', '/portfolio'), undefined)
  assert.equal(getEmbeddedAccessToken(local, 'https://example.com/portfolio'), undefined)
  assert.equal(getEmbeddedAccessToken(local, '//example.com/portfolio'), undefined)
})
